#!/usr/bin/env python3
"""RDME TOML -> README automation runner.

This script is designed to be executed inside *course repos* via a reusable
workflow. Course repos usually do not contain the generator scripts, so this
runner downloads the canonical converter from the central `repos-management`
repository and executes it.

It also manages an idempotent WARNING block at the top of README.md:
- on success (main branch): clears the warning block
- on failure (main branch): ensures a warning block exists

Exit code:
- 0: success (or toml missing -> no-op)
- 1: formatting and/or generation failed
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


WARNING_START = "<!-- RDME_TOML_AUTOGEN_WARNING_START -->"
WARNING_END = "<!-- RDME_TOML_AUTOGEN_WARNING_END -->"

GRADES_SUMMARY_URL = (
    "https://raw.githubusercontent.com/HITSZ-OpenAuto/repos-management/main/"
    "grades_summary.toml"
)


def _append_github_output(key: str, value: str) -> None:
    out = os.getenv("GITHUB_OUTPUT")
    if not out:
        return
    Path(out).write_text("", encoding="utf-8") if not Path(out).exists() else None
    with Path(out).open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"{key}={value}\n")


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _build_block(message: str) -> str:
    msg = (message or "").strip() or "TOML 自动化格式化/生成 README 失败，请检查 readme.toml。"
    lines = [
        WARNING_START,
        "> [!WARNING]",
        f"> {msg}",
        WARNING_END,
        "",
        "",
    ]
    return "\n".join(lines)


def _strip_block(text: str) -> str:
    if WARNING_START not in text:
        return text
    start = text.find(WARNING_START)
    end = text.find(WARNING_END)
    if end == -1:
        return text
    end = end + len(WARNING_END)

    after = text[end:]
    while after.startswith("\n"):
        after = after[1:]
    before = text[:start]
    if before.endswith("\n"):
        before = before[:-1]

    out = (before + "\n" + after) if before else after
    return out.lstrip("\n")


def _ensure_block_at_top(text: str, message: str) -> str:
    text = _strip_block(text)
    block = _build_block(message)
    if not text.strip():
        return block
    return block + text.lstrip("\n")


def _update_warning(readme_path: Path, *, set_warning: bool, message: str = "") -> None:
    text = ""
    if readme_path.exists():
        text = _normalize_newlines(readme_path.read_text(encoding="utf-8"))

    new_text = _ensure_block_at_top(text, message) if set_warning else _strip_block(text)
    if new_text != text:
        readme_path.write_text(new_text, encoding="utf-8", newline="\n")


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "rdme-autogen"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        dest.write_bytes(resp.read())


def _run(cmd: list[str], *, cwd: Path) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    ok = proc.returncode == 0
    out = (proc.stdout or "") + ("\n" if proc.stdout and proc.stderr else "") + (proc.stderr or "")
    return ok, out.strip()


def main() -> int:
    p = argparse.ArgumentParser(description="RDME autogen runner")
    p.add_argument("--toml", default="readme.toml")
    p.add_argument("--readme", default="README.md")
    p.add_argument(
        "--converter-url",
        default=(
            "https://raw.githubusercontent.com/HITSZ-OpenAuto/repos-management/main/"
            "scripts/convert_toml_to_readme.py"
        ),
    )
    args = p.parse_args()

    repo_root = Path.cwd()
    toml_path = repo_root / args.toml
    readme_path = repo_root / args.readme

    is_main = os.getenv("GITHUB_REF") == "refs/heads/main"

    toml_exists = toml_path.exists()
    _append_github_output("toml_exists", "true" if toml_exists else "false")

    if not toml_exists:
        print(f"[rdme] no-op: {toml_path} not found")
        return 0

    fmt_ok = True
    fmt_log = ""
    if shutil.which("taplo") is not None:
        fmt_ok, fmt_log = _run(["taplo", "fmt", str(toml_path)], cwd=repo_root)
    else:
        print("[rdme] taplo not found; skip formatting")

    gen_ok = False
    gen_log = ""
    with tempfile.TemporaryDirectory(prefix="rdme-autogen-") as tmp:
        conv = Path(tmp) / "convert_toml_to_readme.py"
        grades = Path(tmp) / "grades_summary.toml"
        try:
            _download(args.converter_url, conv)
        except Exception as e:
            gen_ok = False
            gen_log = f"download converter failed: {e}"
        else:
            # Best-effort: download grades summary for badge rendering.
            try:
                _download(GRADES_SUMMARY_URL, grades)
            except Exception:
                pass

            # Run converter in tmp so it can discover grades_summary.toml from cwd.
            gen_ok, gen_log = _run(
                [sys.executable, str(conv), "--input", str(toml_path.resolve()), "--overwrite"],
                cwd=Path(tmp),
            )

    ok = fmt_ok and gen_ok

    if is_main:
        if ok:
            _update_warning(readme_path, set_warning=False)
        else:
            msg = "TOML 自动化格式化/生成 README 失败：请检查 readme.toml，并查看 Actions 日志。"
            # Keep README clean: do not dump full logs into warning.
            _update_warning(readme_path, set_warning=True, message=msg)

    if not fmt_ok:
        print("[rdme] taplo fmt failed")
        if fmt_log:
            print(fmt_log)
    if not gen_ok:
        print("[rdme] generate README failed")
        if gen_log:
            print(gen_log)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
