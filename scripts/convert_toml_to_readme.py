#!/usr/bin/env python3
"""Convert readme.toml -> README.md (minimal).

This is a deliberately minimal renderer intended for the "TOML is the source of
truth" workflow:
- Parse TOML
- Emit deterministic Markdown
- Fail loudly (no defensive error handling)

Supported repo types
- normal: renders the unified [[sections]] schema (topic/content)
- multi-project: renders [[courses]] with nested reviews/teachers

CLI
- --input FILE|DIR: convert one file or scan DIR/**/readme.toml
- --all: convert ./final/**/readme.toml

Note
- Assumes upstream has already normalized markdown blocks inside TOML.
- This script intentionally does NOT keep legacy compatibility.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover (Python <= 3.10)
    import tomli as tomllib  # type: ignore


def _s(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def _as_list(v: Any) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _norm_block(text: Any) -> str:
    return _s(text).replace("\r\n", "\n").replace("\r", "\n").strip()


def _iter_authors(author: Any) -> list[dict]:
    if author is None:
        return []
    if isinstance(author, str):
        name = author.strip()
        return [{"name": name, "link": "", "date": ""}] if name else []
    if isinstance(author, dict):
        return [author]
    if isinstance(author, list):
        return [a for a in author if isinstance(a, dict)]
    return []


def _render_author(author: Any, *, indent: str = "") -> str:
    parts: list[str] = []
    for a in _iter_authors(author):
        name = _s(a.get("name")).strip()
        link = _s(a.get("link")).strip()
        date = _s(a.get("date")).strip()
        if not name and not link and not date:
            continue
        disp = f"[{name}]({link})" if (name and link) else (name or link)
        if date:
            disp = f"{disp}, {date}" if disp else date
        if disp:
            parts.append(disp)
    if not parts:
        return ""
    return f"{indent}> 文 / " + ", ".join(parts)


def _render_lecturers(lecturers: Any) -> list[str]:
    lec_list = [x for x in _as_list(lecturers) if isinstance(x, dict)]
    if not lec_list:
        return []

    lines: list[str] = ["## 授课教师", ""]
    for lec in lec_list:
        name = _s(lec.get("name")).strip()
        if not name:
            continue
        lines.append(f"- {name}")

        reviews = [x for x in _as_list(lec.get("reviews")) if isinstance(x, dict)]
        for rv in reviews:
            content = _norm_block(rv.get("content"))
            author = rv.get("author")
            if not content and not author:
                continue

            content_lines = content.split("\n") if content else []
            if content_lines:
                first = content_lines[0].strip()
                lines.append(f"  - {first}" if first else "  -")
                for ln in content_lines[1:]:
                    if ln.strip() == "":
                        continue
                    lines.append("    " + ln)
            else:
                lines.append("  -")

            aq = _render_author(author, indent="    ")
            if aq:
                lines.append("")
                lines.append(aq)

    return lines


def _render_section_items(items: Any) -> list[dict]:
    out: list[dict] = []
    for it in _as_list(items):
        if not isinstance(it, dict):
            continue
        out.append(
            {
                "topic": _s(it.get("topic")).strip(),
                "content": _norm_block(it.get("content")),
                "author": it.get("author"),
            }
        )
    return out


def _render_sections_schema(data: dict) -> str:
    course_name = _s(data.get("course_name")).strip()
    course_code = _s(data.get("course_code")).strip()
    description = _norm_block(data.get("description"))

    lines: list[str] = []
    if course_code and course_name:
        lines.append(f"# {course_code} - {course_name}")
    else:
        lines.append(f"# {course_name or course_code or '课程'}")

    if description:
        lines.append("")
        lines.append(description)

    lec_lines = _render_lecturers(data.get("lecturers"))
    if lec_lines:
        lines.append("")
        lines.extend(lec_lines)

    sections = [x for x in _as_list(data.get("sections")) if isinstance(x, dict)]
    for sec in sections:
        title = _s(sec.get("title")).strip() or "章节"
        items = _render_section_items(sec.get("items"))
        if not items:
            continue

        lines.append("")
        lines.append(f"## {title}")
        for it in items:
            topic = it["topic"]
            content = it["content"]
            author = it["author"]
            if topic:
                lines.append("")
                lines.append(f"### {topic}")
            if content:
                lines.append("")
                lines.append(content)
            aq = _render_author(author)
            if aq:
                lines.append("")
                lines.append(aq)

    return "\n".join(lines).rstrip() + "\n"


def render_multi_project(data: dict) -> str:
    course_name = _s(data.get("course_name")).strip()
    course_code = _s(data.get("course_code")).strip()
    description = _norm_block(data.get("description"))

    lines: list[str] = []
    if course_code and course_name:
        lines.append(f"# {course_code} - {course_name}")
    else:
        lines.append(f"# {course_name or course_code or '课程'}")

    if description:
        lines.append("")
        lines.append(description)

    courses = [x for x in _as_list(data.get("courses")) if isinstance(x, dict)]
    for c in courses:
        name = _s(c.get("name")).strip()
        code = _s(c.get("code")).strip()
        header = " - ".join([x for x in [code, name] if x]) or "课程"

        lines.append("")
        lines.append(f"## {header}")

        reviews = [x for x in _as_list(c.get("reviews")) if isinstance(x, dict)]
        if reviews:
            lines.append("")
            lines.append(f"### {header} - 课程评价")

            buckets: dict[str, list[dict]] = {}
            order: list[str] = []
            for rv in reviews:
                topic = _s(rv.get("topic")).strip()
                if topic not in buckets:
                    buckets[topic] = []
                    order.append(topic)
                buckets[topic].append(rv)

            for topic in order:
                if topic and topic != "课程评价":
                    lines.append("")
                    lines.append(f"#### {header} - {topic}")
                for rv in buckets[topic]:
                    content = _norm_block(rv.get("content"))
                    author = rv.get("author")
                    if content:
                        lines.append("")
                        lines.append(content)
                    aq = _render_author(author)
                    if aq:
                        lines.append("")
                        lines.append(aq)

        teachers = [x for x in _as_list(c.get("teachers")) if isinstance(x, dict)]
        for t in teachers:
            tname = _s(t.get("name")).strip()
            if not tname:
                continue
            lines.append("")
            lines.append(f"### {header} - {tname}")

            trevs = [x for x in _as_list(t.get("reviews")) if isinstance(x, dict)]
            if not trevs:
                continue

            tbuckets: dict[str, list[dict]] = {}
            torder: list[str] = []
            for rv in trevs:
                topic = _s(rv.get("topic")).strip()
                if topic not in tbuckets:
                    tbuckets[topic] = []
                    torder.append(topic)
                tbuckets[topic].append(rv)

            for topic in torder:
                if topic:
                    lines.append("")
                    lines.append(f"#### {header} - {tname} - {topic}")
                for rv in tbuckets[topic]:
                    content = _norm_block(rv.get("content"))
                    author = rv.get("author")
                    if content:
                        lines.append("")
                        lines.append(content)
                    aq = _render_author(author)
                    if aq:
                        lines.append("")
                        lines.append(aq)

    misc = [x for x in _as_list(data.get("misc")) if isinstance(x, dict)]
    if misc:
        lines.append("")
        lines.append("## 其他")
        for it in misc:
            topic = _s(it.get("topic")).strip()
            content = _norm_block(it.get("content"))
            author = it.get("author")
            if topic:
                lines.append("")
                lines.append(f"### {topic}")
            if content:
                lines.append("")
                lines.append(content)
            aq = _render_author(author)
            if aq:
                lines.append("")
                lines.append(aq)

    return "\n".join(lines).rstrip() + "\n"


def render_readme(data: dict) -> str:
    repo_type = _s(data.get("repo_type")).strip().lower()
    if repo_type == "multi-project":
        return render_multi_project(data)
    if not isinstance(data.get("sections"), list):
        raise ValueError("normal repo requires unified [[sections]] schema")
    return _render_sections_schema(data)


def _iter_readme_tomls(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(root.rglob("readme.toml"))


def _default_out_path(input_path: Path) -> Path:
    if input_path.name.lower() == "readme.toml":
        return input_path.with_name("README.md")
    return input_path.with_name(f"{input_path.stem}_README.md")


def main() -> int:
    p = argparse.ArgumentParser(description="Convert readme.toml to README.md (minimal).")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="Convert ./final/**/readme.toml -> ./final/**/README.md")
    g.add_argument("--input", "-i", help="Input TOML file or a directory to scan")
    p.add_argument("--output", "-o", help="Output path (only valid when --input is a single file)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing README")
    args = p.parse_args()

    root = Path("final") if args.all else Path(args.input)
    toml_paths = _iter_readme_tomls(root)
    if not toml_paths:
        return 0

    if args.output and len(toml_paths) != 1:
        raise ValueError("--output can only be used with a single input file")

    for toml_path in toml_paths:
        out = Path(args.output) if args.output else _default_out_path(toml_path)
        if out.exists() and not args.overwrite:
            continue
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        out.write_text(render_readme(data), encoding="utf-8", newline="\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
