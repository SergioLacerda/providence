#!/usr/bin/env python3
"""Internal markdown link checker/fixer for docs/ tree."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# Repo root is two levels up from tools/docs/. This script is invoked as a
# standalone subprocess (make_tasks.py's docs-link-check/-fix), not imported,
# so it cannot rely on providence_core being pip/uv-installed into the active venv —
# same guard as tools/maintenance/lint_all.py.
REPO_ROOT = Path(__file__).resolve().parents[2]
_PROVIDENCE_CORE_SRC = REPO_ROOT / "packages" / "core" / "providence_core" / "src"
if str(_PROVIDENCE_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(_PROVIDENCE_CORE_SRC))

from providence_core.utils.process import (  # noqa: E402
    ProcessNonZeroExitError,
    SafeProcessRunner,
)

LINK_RE: Final[re.Pattern[str]] = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
MAPPING_RULES: Final[tuple[tuple[str, str], ...]] = (
    ("/docs/ia/CANONICAL/", "docs/spec/canonical/"),
    ("/docs/ia/", "docs/spec/"),
    ("../EXECUTION/_START_HERE.md", "spec/guides/operational/CORE__START_HERE.md"),
    ("../CANONICAL/", "spec/canonical/"),
    ("../INTEGRATION/", "spec/guides/integration/"),
    ("../decisions/ADR-001.md", "spec/decisions/ADR-001-clean-architecture-8-layer.md"),
)


@dataclass(frozen=True)
class BrokenLink:
    file: Path
    line: int
    target: str
    bucket: str
    suggestion: str | None


def is_internal_relative(target: str) -> bool:
    return target.startswith("./") or target.startswith("../")


def strip_anchor_and_query(target: str) -> str:
    no_anchor = target.split("#", maxsplit=1)[0]
    return no_anchor.split("?", maxsplit=1)[0]


def resolve_target(md_file: Path, target: str, repo_root: Path) -> Path:
    relative = strip_anchor_and_query(target)
    return (md_file.parent / relative).resolve().relative_to(repo_root.resolve())


def apply_mapping(target: str) -> str | None:
    for old, new in MAPPING_RULES:
        if old in target:
            return target.replace(old, new)
    if "../decisions/ADR-" in target and target.endswith(".md"):
        stem = Path(target).stem
        return target.replace(f"../decisions/{stem}.md", f"spec/decisions/{stem}")
    return None


def classify_links(repo_root: Path, docs_root: Path) -> list[BrokenLink]:
    return classify_links_for_files(repo_root, list(docs_root.rglob("*.md")))


def classify_links_for_files(repo_root: Path, files: list[Path]) -> list[BrokenLink]:
    issues: list[BrokenLink] = []
    for md_file in files:
        text = md_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in LINK_RE.finditer(line):
                target = match.group(1).strip()
                if not is_internal_relative(target):
                    continue
                try:
                    resolved = resolve_target(md_file, target, repo_root)
                except ValueError:
                    continue
                if (repo_root / resolved).exists():
                    continue
                mapped = apply_mapping(target)
                if mapped is not None:
                    try:
                        mapped_resolved = resolve_target(md_file, mapped, repo_root)
                    except ValueError:
                        mapped_resolved = None
                    if (
                        mapped_resolved is not None
                        and (repo_root / mapped_resolved).exists()
                    ):
                        issues.append(
                            BrokenLink(
                                file=md_file.relative_to(repo_root),
                                line=lineno,
                                target=target,
                                bucket="auto-fixable",
                                suggestion=mapped,
                            )
                        )
                        continue
                bucket = "needs-creation" if "runbook" in target.lower() else "orphan"
                issues.append(
                    BrokenLink(
                        file=md_file.relative_to(repo_root),
                        line=lineno,
                        target=target,
                        bucket=bucket,
                        suggestion=None,
                    )
                )
    return issues


def run_fix(files: list[Path]) -> int:
    changed = 0
    for md_file in files:
        original = md_file.read_text(encoding="utf-8")
        updated = original
        for old, new in MAPPING_RULES:
            updated = updated.replace(old, new)
        if updated != original:
            md_file.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"Applied deterministic mapping fixes to {changed} file(s).")
    return 0


def print_report(issues: list[BrokenLink]) -> None:
    if not issues:
        print("No broken internal relative links found.")
        return
    for issue in issues:
        message = f"{issue.bucket.upper()}: {issue.file}:{issue.line} -> {issue.target}"
        if issue.suggestion:
            message += f" | suggestion: {issue.suggestion}"
        print(message)
    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue.bucket] = counts.get(issue.bucket, 0) + 1
    print("Summary:")
    for bucket in ("auto-fixable", "orphan", "needs-creation"):
        print(f"  {bucket}: {counts.get(bucket, 0)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check internal markdown links in docs/."
    )
    parser.add_argument("--mode", choices=("audit", "fix", "ci"), required=True)
    parser.add_argument(
        "--docs-root", default="docs", help="Docs directory root (default: docs)"
    )
    parser.add_argument(
        "--changed-file",
        action="append",
        default=[],
        help="Relative path to changed file. Can be repeated.",
    )
    parser.add_argument(
        "--changed-files-from-git",
        action="store_true",
        help="Resolve changed files via `git diff --name-only`.",
    )
    parser.add_argument(
        "--base-ref",
        default="",
        help="Base git ref for changed-files diff (used with --changed-files-from-git).",
    )
    parser.add_argument(
        "--head-ref",
        default="HEAD",
        help="Head git ref for changed-files diff (used with --changed-files-from-git).",
    )
    return parser.parse_args()


def _collect_changed_files_from_git(
    repo_root: Path, base_ref: str, head_ref: str
) -> list[str]:
    if not base_ref:
        raise ValueError("--base-ref is required when --changed-files-from-git is set")
    proc = SafeProcessRunner().run(
        ["git", "diff", "--name-only", base_ref, head_ref],
        cwd=repo_root,
        check=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _resolve_target_files(
    repo_root: Path, docs_root: Path, changed_files: list[str]
) -> list[Path]:
    if not changed_files:
        return list(docs_root.rglob("*.md"))
    resolved: list[Path] = []
    for rel in changed_files:
        p = (repo_root / rel).resolve()
        if not p.exists() or p.suffix.lower() != ".md":
            continue
        try:
            p.relative_to(docs_root)
        except ValueError:
            continue
        resolved.append(p)
    unique = sorted(set(resolved))
    return unique


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()
    docs_root = (repo_root / args.docs_root).resolve()
    if not docs_root.exists():
        print(f"Docs root not found: {docs_root}", file=sys.stderr)
        return 2

    changed_files = list(args.changed_file)
    if args.changed_files_from_git:
        try:
            changed_files.extend(
                _collect_changed_files_from_git(repo_root, args.base_ref, args.head_ref)
            )
        except (ValueError, ProcessNonZeroExitError) as exc:
            print(f"Failed to collect changed files from git: {exc}", file=sys.stderr)
            return 2

    target_files = _resolve_target_files(repo_root, docs_root, changed_files)
    if changed_files and not target_files:
        print("No changed markdown files under docs/ to check.")
        return 0

    if args.mode == "fix":
        return run_fix(target_files)

    issues = classify_links_for_files(repo_root, target_files)
    print_report(issues)

    if args.mode == "ci":
        unresolved = [i for i in issues if i.bucket != "auto-fixable"]
        return 1 if unresolved else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
