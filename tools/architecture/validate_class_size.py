#!/usr/bin/env python3
"""
Validate class size and module size guardrails for Python source files.

Both checks are blocking (ADR-019, docs/adr/ADR-019-guardrail-complexity-budget.md).
Pre-existing module-size violations are grandfathered via
tools/architecture/module_size_allowlist.json; class-size violations via
tools/architecture/class_size_allowlist.json. New violations of either are not
allowlisted — split the file instead.

Usage:
    python tools/architecture/validate_class_size.py [--root <path>] [--max-lines 400] [--show-module-warnings] [--module-warning-lines 400] [--json]
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, cast

SKIP_MARKERS = ("site-packages", ".venv", "__pycache__", ".egg", "generated", "tests")
# Exact path-segment match, not a substring — "build" as a substring would also
# hit real source like .../builders/pipeline_builder.py. Excludes gitignored
# build-output directories (e.g. packages/interfaces/providence_cli/build/lib/...),
# never hand-maintained source.
SKIP_SEGMENTS = ("build",)
ALLOWLIST_FILE = "tools/architecture/class_size_allowlist.json"
MODULE_ALLOWLIST_FILE = "tools/architecture/module_size_allowlist.json"


def _is_skipped(rel_parts: tuple[str, ...]) -> bool:
    return any(part in SKIP_SEGMENTS for part in rel_parts)


def _path_sort_key(path: str) -> tuple[str, ...]:
    """Sort by module/file path segments for deterministic grouping."""
    return tuple(path.split("/"))


def _is_repo_root(path: Path) -> bool:
    return (path / "pyproject.toml").exists() and (path / "packages").exists()


def _detect_root(explicit_root: Path | None) -> Path:
    if explicit_root is not None:
        return explicit_root.resolve()
    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if _is_repo_root(candidate):
            return candidate
    raise RuntimeError("Could not detect repo root. Use --root.")


def _load_allowlist(root: Path) -> dict[str, str]:
    path = root / ALLOWLIST_FILE
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("allowlist", {})
    if not isinstance(entries, dict):
        return {}
    return {str(k).replace("\\", "/"): str(v) for k, v in entries.items()}


def _load_module_allowlist(root: Path) -> dict[str, str]:
    path = root / MODULE_ALLOWLIST_FILE
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("allowlist", {})
    if not isinstance(entries, dict):
        return {}
    return {str(k).replace("\\", "/"): str(v) for k, v in entries.items()}


def _scan_classes(
    root: Path, max_lines: int, allowlist: dict[str, str]
) -> dict[str, object]:
    violations: list[dict[str, object]] = []
    scanned = 0

    for file in (root / "packages").rglob("*.py"):
        if any(marker in str(file) for marker in SKIP_MARKERS):
            continue
        rel = file.relative_to(root).as_posix()
        if _is_skipped(file.relative_to(root).parts):
            continue
        try:
            src = file.read_text(encoding="utf-8")
            tree = ast.parse(src, filename=str(file))
        except (UnicodeDecodeError, SyntaxError):
            continue
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            scanned += 1
            end = getattr(node, "end_lineno", None)
            if end is None:
                continue
            start = node.lineno
            length = end - start + 1
            class_id = f"{rel}:{node.name}"
            if length > max_lines and class_id not in allowlist:
                violations.append(
                    {
                        "class_id": class_id,
                        "path": rel,
                        "class_name": node.name,
                        "start": start,
                        "end": end,
                        "line_count": length,
                    }
                )

    violations.sort(key=lambda x: _path_sort_key(str(x["path"])))
    return {
        "ok": len(violations) == 0,
        "max_lines": max_lines,
        "violations": violations,
        "violations_count": len(violations),
        "classes_scanned": scanned,
        "allowlist_count": len(allowlist),
    }


def _scan_modules(
    root: Path, warning_lines: int, allowlist: dict[str, str]
) -> dict[str, object]:
    """Module-size scan. `warnings` here are blocking violations (ADR-019) unless
    the module's path is in `allowlist` — the name is kept for output-shape
    compatibility with existing callers (`--show-module-warnings` display), not
    because these are non-blocking anymore.
    """
    warnings: list[dict[str, object]] = []
    scanned = 0

    for file in (root / "packages").rglob("*.py"):
        if any(marker in str(file) for marker in SKIP_MARKERS):
            continue
        if _is_skipped(file.relative_to(root).parts):
            continue
        try:
            src = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        line_count = src.count("\n") + (1 if src else 0)
        rel = file.relative_to(root).as_posix()
        if line_count > warning_lines and rel not in allowlist:
            warnings.append({"path": rel, "line_count": line_count})

    warnings.sort(key=lambda x: _path_sort_key(str(x["path"])))
    return {
        "ok": len(warnings) == 0,
        "warning_lines": warning_lines,
        "warnings": warnings,
        "warnings_count": len(warnings),
        "modules_scanned": scanned,
        "allowlist_count": len(allowlist),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate class size guardrail")
    parser.add_argument("--root", type=Path, default=None, help="Repo root")
    parser.add_argument(
        "--max-lines", type=int, default=400, help="Maximum lines per class"
    )
    parser.add_argument(
        "--module-warning-lines",
        type=int,
        default=400,
        help="Fail when a Python module exceeds this line count, unless the "
        f"module's path is listed in {MODULE_ALLOWLIST_FILE} (ADR-019)",
    )
    parser.add_argument(
        "--show-module-warnings",
        action="store_true",
        help="Show module size violations in text output (they always affect "
        "the exit code regardless of this flag — see ADR-019)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    try:
        root = _detect_root(args.root)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    allowlist = _load_allowlist(root)
    report = _scan_classes(root, args.max_lines, allowlist)
    violations = cast(list[dict[str, Any]], report.get("violations", []))

    module_allowlist = _load_module_allowlist(root)
    module_report = _scan_modules(root, args.module_warning_lines, module_allowlist)
    module_warnings = cast(list[dict[str, Any]], module_report.get("warnings", []))

    if args.json:
        payload: dict[str, object] = {
            "class_report": report,
            "module_report": module_report,
        }
        print(json.dumps(payload, indent=2))
    elif report["ok"]:
        print(
            f"Class size OK: scanned {report['classes_scanned']} classes with max {report['max_lines']} lines."
        )
    else:
        print(
            f"ERROR: {report['violations_count']} class(es) exceed {report['max_lines']} lines (excluding allowlist):\n"
        )
        for item in violations:
            print(
                f"  - {item['class_id']} lines={item['line_count']} ({item['start']}-{item['end']})"
            )
        print(
            f"\nTo allow temporary exceptions, add class ids to {ALLOWLIST_FILE} with a justification."
        )

    if not args.json and module_warnings:
        print(
            f"ERROR: {module_report['warnings_count']} module(s) exceed "
            f"{module_report['warning_lines']} lines (blocking, ADR-019 — grandfathered "
            f"paths in {MODULE_ALLOWLIST_FILE} are excluded):"
        )
        for item in module_warnings[:20]:
            print(f"  - {item['path']} lines={item['line_count']}")
        if len(module_warnings) > 20:
            print(f"  ... +{len(module_warnings) - 20} more")
        print(
            f"\nTo grandfather a pre-existing violation, add its path to "
            f"{MODULE_ALLOWLIST_FILE} with a justification (see ADR-019). New "
            "violations should be split instead of allowlisted."
        )

    return 0 if (report["ok"] and module_report["ok"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
