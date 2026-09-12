#!/usr/bin/env python3
"""
Validate inter-layer import rules for the Providence monorepo.

Layer detection: derived from the `packages/<layer>/` directory segment.
Rules define which layers a given layer is NOT allowed to import from.

Usage:
    python tools/architecture/validate_imports.py [--root <path>]
"""

import ast
import json
import sys
from pathlib import Path

# Layer names match the directory under packages/ (e.g. packages/core → "core").
# Value = set of layers this layer must NOT import from.
FORBIDDEN: dict[str, set[str]] = {
    "core": {"interfaces"},  # core must not import from interfaces (cli/wizard)
    "features": {"interfaces"},  # features must not import from interfaces
    "interfaces": set(),  # interfaces may import from core and features
}

# Package prefixes that identify intra-project imports (underscore convention).
PROVIDENCE_PREFIXES = (
    "providence_core",
    "providence_telemetry",
    "providence_integration",
    "providence_cli",
    "providence_wizard",
)

ALLOWLIST_FILE = "tools/architecture/imports_allowlist.json"


def _load_allowlist(root: Path) -> dict[str, set[str]]:
    path = root / ALLOWLIST_FILE
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("allowlist", {})
    if not isinstance(entries, dict):
        return {}
    normalized: dict[str, set[str]] = {}
    for rel_path, modules in entries.items():
        if isinstance(modules, list):
            normalized[str(rel_path)] = {str(m) for m in modules}
    return normalized


def _get_layer(path: Path, root: Path) -> str | None:
    """Return the layer name for a file, or None if not under packages/."""
    try:
        rel = path.relative_to(root / "packages")
        return rel.parts[0] if rel.parts else None
    except ValueError:
        return None


def _target_layer(module: str) -> str | None:
    """Map a module name to its layer, or None if not a Providence module."""
    for prefix in PROVIDENCE_PREFIXES:
        if module == prefix or module.startswith(prefix + "."):
            if prefix in ("providence_core", "providence_telemetry"):
                return "core"
            if prefix == "providence_integration":
                return "features"
            if prefix in ("providence_cli", "providence_wizard"):
                return "interfaces"
    return None


def _check_file_violations(
    file: Path, layer: str, root: Path, allowlist: dict[str, set[str]]
) -> tuple[list[str], str | None]:
    """Return violation strings for a single Python file."""
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
    except SyntaxError:
        return [], str(file.relative_to(root))

    violations: list[str] = []
    forbidden = FORBIDDEN.get(layer, set())
    rel = file.relative_to(root)

    allowed = allowlist.get(str(rel), set())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue
        if isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            if module_name in allowed:
                continue
            tl = _target_layer(node.module or "")
            if tl and tl in forbidden:
                violations.append(
                    f"{rel}:{node.lineno}: layer '{layer}' imports from forbidden layer '{tl}' ({module_name})"
                )
        else:
            for alias in node.names:
                if alias.name in allowed:
                    continue
                tl = _target_layer(alias.name)
                if tl and tl in forbidden:
                    violations.append(
                        f"{rel}:{node.lineno}: layer '{layer}' imports from forbidden layer '{tl}' ({alias.name})"
                    )
    return violations, None


def validate(root: Path) -> tuple[list[str], list[str]]:
    """Return (violations, parse_errors)."""
    violations: list[str] = []
    parse_errors: list[str] = []
    skip_markers = ("site-packages", ".venv", "__pycache__", ".egg")
    allowlist = _load_allowlist(root)

    for file in root.rglob("*.py"):
        if any(m in str(file) for m in skip_markers):
            continue
        if "/tests/" in str(file).replace("\\", "/"):
            continue
        layer = _get_layer(file, root)
        if layer is None or layer not in FORBIDDEN:
            continue
        file_violations, parse_error = _check_file_violations(
            file, layer, root, allowlist
        )
        violations.extend(file_violations)
        if parse_error is not None:
            parse_errors.append(parse_error)

    return violations, parse_errors


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate Providence inter-layer import rules"
    )
    parser.add_argument(
        "--root", type=Path, default=None, help="Repo root (default: auto-detect)"
    )
    args = parser.parse_args()

    root = args.root
    if root is None:
        # Auto-detect: walk up from this file looking for packages/ + pyproject.toml
        here = Path(__file__).resolve()
        for candidate in [here.parent, *here.parents]:
            if (candidate / "packages").is_dir() and (
                candidate / "pyproject.toml"
            ).is_file():
                root = candidate
                break
        if root is None:
            print("ERROR: Could not detect repo root. Use --root.", file=sys.stderr)
            return 1

    violations, parse_errors = validate(root)

    if violations:
        print(f"\nERROR: {len(violations)} architecture violation(s):\n")
        for v in violations:
            print(f"  {v}")
        print()
        return 1
    if parse_errors:
        print(f"\nERROR: {len(parse_errors)} file(s) could not be parsed:\n")
        for path in parse_errors:
            print(f"  - {path}")
        print("\nFix syntax errors before running architecture validation.")
        return 1

    print("Architecture OK: no forbidden inter-layer imports found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
