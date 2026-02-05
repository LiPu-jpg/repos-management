#!/usr/bin/env python3
"""Insert or remove an auto-generation WARNING block at the very top of README.md.

This is intended for course repos where README is generated from readme.toml.

- On failure: ensure a visible warning block exists.
- On success: optionally clear the warning block.

The block is delimited by HTML comments so it is idempotent.
"""

from __future__ import annotations

import argparse
from pathlib import Path

WARNING_START = "<!-- RDME_TOML_AUTOGEN_WARNING_START -->"
WARNING_END = "<!-- RDME_TOML_AUTOGEN_WARNING_END -->"


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
    # Remove trailing newlines after end marker.
    after = text[end:]
    while after.startswith("\n"):
        after = after[1:]
    before = text[:start]
    if before.endswith("\n"):
        before = before[:-1]
    # Ensure file doesn't start with extra blank lines.
    out = (before + "\n" + after) if before else after
    return out.lstrip("\n")


def _ensure_block_at_top(text: str, message: str) -> str:
    text = _strip_block(text)
    block = _build_block(message)
    if not text.strip():
        return block
    return block + text.lstrip("\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Add/clear RDME TOML autogen warning block in README")
    p.add_argument("--readme", default="README.md")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--set", action="store_true", help="Ensure warning block exists at top")
    g.add_argument("--clear", action="store_true", help="Remove warning block if present")
    p.add_argument("--message", default="")
    args = p.parse_args()

    path = Path(args.readme)
    text = ""
    if path.exists():
        text = _normalize_newlines(path.read_text(encoding="utf-8"))

    if args.set:
        new_text = _ensure_block_at_top(text, args.message)
    else:
        new_text = _strip_block(text)

    # Only write when changed.
    if new_text != text:
        path.write_text(new_text, encoding="utf-8", newline="\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
