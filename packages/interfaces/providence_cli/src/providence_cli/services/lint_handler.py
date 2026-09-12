"""Pure markdown/spec checking functions for lint commands."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

import typer

from providence_cli.services._lint_handler_support import (
    collect_active_markdown_files,
    collect_anchor_files,
    extract_file_anchors,
    filter_code_blocks,
    resolve_link_target,
    slugify_anchor,
)


def _slugify_anchor(value: str) -> str:
    return slugify_anchor(value)


def _extract_file_anchors(file_path: Path) -> set[str]:
    return extract_file_anchors(file_path, slugify_anchor_fn=_slugify_anchor)


def _filter_code_blocks(content: str) -> list[str]:
    return filter_code_blocks(content)


def _resolve_link_target(source_file: Path, raw_target: str) -> tuple[Path, str] | None:
    return resolve_link_target(source_file, raw_target)


def _validate_markdown_anchors(markdown_files: list[Path], repo_root: Path) -> int:
    """Validate local markdown links and anchor fragments."""
    errors = 0
    anchors_cache: dict[Path, set[str]] = {}
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

    for source_file in markdown_files:
        filtered_content = "\n".join(
            _filter_code_blocks(source_file.read_text(encoding="utf-8"))
        )
        for match in link_pattern.finditer(filtered_content):
            result = _resolve_link_target(source_file, match.group(1).strip())
            if result is None:
                continue
            target_file, fragment = result
            if not fragment:
                continue
            if target_file not in anchors_cache:
                anchors_cache[target_file] = _extract_file_anchors(target_file)
            normalized = _slugify_anchor(fragment)
            anchors = anchors_cache[target_file]
            if (
                normalized
                and normalized not in anchors
                and unquote(fragment).lower() not in anchors
            ):
                typer.echo(
                    f"   {source_file.relative_to(repo_root)}: "
                    f"anchor '#{fragment}' not found in {target_file.relative_to(repo_root)}"
                )
                errors += 1

    return errors


def _validate_link_fragment_style(
    source_file: Path, raw_target: str, repo_root: Path
) -> int:
    """Validate a single link's fragment for style violations. Returns 0 or 1 error count."""
    if not raw_target:
        return 0
    target = raw_target.split()[0]
    if target.startswith(("http://", "https://", "mailto:", "tel:")):
        return 0
    fragment = ""
    if target.startswith("#"):
        fragment = target[1:]
    elif "#" in target:
        _, fragment = target.split("#", 1)
    if not fragment:
        return 0
    if "%" in fragment:
        typer.echo(
            f"   {source_file.relative_to(repo_root)}: URL-encoded anchor fragment '#{fragment}' is not allowed"
        )
        return 1
    if not _slugify_anchor(fragment):
        typer.echo(
            f"   {source_file.relative_to(repo_root)}: anchor fragment '#{fragment}' resolves to empty slug"
        )
        return 1
    return 0


def _validate_anchor_style(markdown_files: list[Path], repo_root: Path) -> int:
    """Validate fragile or non-standard anchor usage patterns."""
    errors = 0
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

    for source_file in markdown_files:
        filtered_lines = _filter_code_blocks(source_file.read_text(encoding="utf-8"))
        filtered_content = "\n".join(filtered_lines)

        for match in link_pattern.finditer(filtered_content):
            errors += _validate_link_fragment_style(
                source_file, match.group(1).strip(), repo_root
            )

        for line_number, line in enumerate(filtered_lines, start=1):
            if re.match(r"^#{1,6}\s+", line) and line.rstrip() != line:
                typer.echo(
                    f"   {source_file.relative_to(repo_root)}:{line_number}: "
                    "heading has trailing whitespace, which can destabilize generated anchors"
                )
                errors += 1

    return errors


def _collect_active_markdown_files(repo_root: Path) -> list[Path]:
    return collect_active_markdown_files(repo_root)


def _check_legacy_patterns(canonical_dir: Path, repo_root: Path) -> int:
    """Check for legacy path references in canonical docs. Returns error count."""
    patterns = [
        (re.compile(r"docs/specs"), "Legacy 'docs/specs' used (should be docs/spec)"),
        (re.compile(r"(?<!\.providence)/runtime/"), "Legacy '/runtime/' reference"),
        (re.compile(r"/REALITY/"), "Legacy '/REALITY/' reference"),
        (re.compile(r"/DEVELOPMENT/"), "Legacy '/DEVELOPMENT/' reference"),
        (
            re.compile(r"providence-generated"),
            "Legacy 'providence-generated' reference",
        ),
    ]
    errors = 0
    for file in canonical_dir.rglob("*.md"):
        content = file.read_text(encoding="utf-8")
        for pattern, msg in patterns:
            if pattern.search(content):
                typer.echo(f"   {file.relative_to(repo_root)}: {msg}")
                errors += 1
    return errors


def _check_project_leaks(canonical_dir: Path, repo_root: Path) -> int:
    """Check for project-specific identifier leaks in canonical core docs. Returns error count."""
    patterns = [
        (re.compile(r"rpg-narrative-server"), "Project leak: rpg-narrative-server"),
        (re.compile(r"game-master"), "Project leak: game-master"),
    ]
    errors = 0
    for file in (canonical_dir / "core").rglob("*.md"):
        content = file.read_text(encoding="utf-8")
        for pattern, msg in patterns:
            if pattern.search(content):
                typer.echo(f"   {file.relative_to(repo_root)}: {msg}")
                errors += 1
    return errors


def _collect_anchor_files(repo_root: Path, validate_all_anchors: bool) -> list[Path]:
    return collect_anchor_files(
        repo_root,
        validate_all_anchors,
        collect_active_markdown_files_fn=_collect_active_markdown_files,
        echo_fn=typer.echo,
    )
