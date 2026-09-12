"""Support helpers for markdown/spec lint routines."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote


def slugify_anchor(value: str) -> str:
    text = unquote(value).strip().lstrip("#").lower()
    text = re.sub(r"\{#([A-Za-z0-9._:-]+)\}\s*$", "", text).strip()
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("`", "").replace("*", "").replace("_", "")
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"[-\s]+", "-", text).strip("-")


def extract_file_anchors(file_path: Path, *, slugify_anchor_fn: Any) -> set[str]:
    anchors: set[str] = set()
    content = file_path.read_text(encoding="utf-8")
    for explicit_id in re.findall(r"\{#([A-Za-z0-9._:-]+)\}", content):
        anchors.add(explicit_id.strip().lower())
    in_fenced_code = False
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fenced_code = not in_fenced_code
            continue
        if in_fenced_code:
            continue
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if not match:
            continue
        heading = re.sub(r"\s+#+\s*$", "", match.group(1)).strip()
        explicit_match = re.search(r"\{#([A-Za-z0-9._:-]+)\}\s*$", heading)
        if explicit_match:
            anchors.add(explicit_match.group(1).strip().lower())
            heading = re.sub(r"\s*\{#[A-Za-z0-9._:-]+\}\s*$", "", heading).strip()
        slug = slugify_anchor_fn(heading)
        if slug:
            anchors.add(slug)
    return anchors


def filter_code_blocks(content: str) -> list[str]:
    in_fenced_code = False
    filtered_lines: list[str] = []
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fenced_code = not in_fenced_code
            filtered_lines.append(line)
            continue
        filtered_lines.append("" if in_fenced_code else line)
    return filtered_lines


def resolve_link_target(source_file: Path, raw_target: str) -> tuple[Path, str] | None:
    if not raw_target:
        return None
    if raw_target.startswith("<") and raw_target.endswith(">"):
        raw_target = raw_target[1:-1]
    target = raw_target.split()[0]
    if target.startswith(("http://", "https://", "mailto:", "tel:")):
        return None
    if target.startswith("#"):
        return source_file, target[1:]
    rel_path, fragment = target.split("#", 1) if "#" in target else (target, "")
    candidate = (source_file.parent / unquote(rel_path)).resolve()
    return None if not candidate.exists() else (candidate, fragment)


def collect_active_markdown_files(repo_root: Path) -> list[Path]:
    files = set()
    docs_dir = repo_root / "docs"
    if docs_dir.exists():
        for file in docs_dir.rglob("*.md"):
            if "archive" not in file.parts:
                files.add(file.resolve())
    for name in ("README.md", "readme-detailed.md", "readme-client.md"):
        candidate = repo_root / name
        if candidate.exists():
            files.add(candidate.resolve())
    return sorted(files)


def collect_anchor_files(
    repo_root: Path,
    validate_all_anchors: bool,
    *,
    collect_active_markdown_files_fn: Any,
    echo_fn: Any,
) -> list[Path]:
    if validate_all_anchors:
        files = collect_active_markdown_files_fn(repo_root)
        echo_fn(
            f" Checking markdown anchors in active docs scope ({len(files)} files)..."
        )
        return cast(list[Path], files)
    wizard_docs_dir = (
        repo_root / "docs" / "spec" / "reality" / "implementation-analyses" / "wizard"
    )
    if not wizard_docs_dir.exists():
        return []
    files = [
        f
        for f in [
            wizard_docs_dir / "START_HERE_FOR_DOCUMENTATION.md",
            wizard_docs_dir / "WIZARD_DOCUMENTATION_INDEX.md",
        ]
        if f.exists()
    ]
    if files:
        echo_fn(" Checking markdown anchors in wizard entry docs...")
    return files
