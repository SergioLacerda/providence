#!/usr/bin/env python3
"""Generate JSON Schema files from Pydantic contract models.

Schema files are the canonical contract for governance artifact consumers.
When a Pydantic model changes, regenerate and commit the schema together.

Usage:
    make generate-schemas                                      # Recommended
    uv run python tools/testing/generate-schemas.py           # Generate all
    uv run python tools/testing/generate-schemas.py --dry-run # Preview changes
"""

import difflib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
_PROVIDENCE_CORE_SRC = REPO_ROOT / "packages" / "core" / "providence_core" / "src"
if str(_PROVIDENCE_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(_PROVIDENCE_CORE_SRC))

SCHEMAS_DIR = REPO_ROOT / "tests" / "contract" / "schemas"

# Each entry: model_import -> output schema file
SCHEMA_TARGETS: list[dict[str, Any]] = [
    {
        "module": "tests.contract.models",
        "class": "GovernanceCoreArtifact",
        "output": SCHEMAS_DIR / "governance_core.schema.json",
    },
]


def _load_model_class(module_name: str, class_name: str) -> Any:
    import importlib

    mod = importlib.import_module(module_name)
    return getattr(mod, class_name)


def generate_schema(target: dict[str, Any], dry_run: bool = False) -> bool:
    """Generate a single JSON Schema file. Returns True on success."""
    module_name = target["module"]
    class_name = target["class"]
    output_path: Path = target["output"]

    try:
        model_cls = _load_model_class(module_name, class_name)
    except (ImportError, AttributeError) as exc:
        print(f"ERROR: Cannot import {module_name}.{class_name}: {exc}")
        return False

    current_schema = model_cls.model_json_schema()
    new_content = json.dumps(current_schema, indent=2, sort_keys=True) + "\n"

    old_lines: list[str] = []
    if output_path.exists():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        if existing == current_schema:
            print(f"No change: {output_path.name} is already up to date.")
            return True
        old_lines = json.dumps(existing, indent=2, sort_keys=True).splitlines(
            keepends=True
        )

    new_lines = json.dumps(current_schema, indent=2, sort_keys=True).splitlines(
        keepends=True
    )
    diff = "".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="schema (before)",
            tofile="schema (after)",
            n=3,
        )
    )
    print(f"\n--- diff for {output_path.name} ---")
    print(diff or "(new file)")

    if dry_run:
        print(f"[DRY RUN] Would write {len(new_content)} bytes to {output_path}")
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(new_content, encoding="utf-8")
    print(f"Updated: {output_path}")
    return True


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate JSON Schema files from Pydantic contract models.",
        epilog="Tip: use 'make generate-schemas' as the canonical entry point.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing any files",
    )
    args = parser.parse_args()

    # Ensure tests package is importable
    tests_src = REPO_ROOT / "tests"
    if str(tests_src) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    return (
        0
        if all(generate_schema(t, dry_run=args.dry_run) for t in SCHEMA_TARGETS)
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
