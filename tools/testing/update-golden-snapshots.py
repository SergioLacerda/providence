#!/usr/bin/env python3
"""Update golden-file snapshots for contract tests.

Golden files are the canonical reference for compiled artifacts. When governance
compilation changes intentionally, use this script to update the fixtures.

Usage:
    make update-golden-snapshots                                    # Recommended
    uv run python tools/testing/update-golden-snapshots.py         # Compile + update all
    uv run python tools/testing/update-golden-snapshots.py --dry-run  # Preview changes
"""

import difflib
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
_PROVIDENCE_CORE_SRC = REPO_ROOT / "packages" / "core" / "providence_core" / "src"
if str(_PROVIDENCE_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(_PROVIDENCE_CORE_SRC))
from providence_core.utils.text_io import read_text_utf8, write_text_utf8  # noqa: E402

COMPILED = REPO_ROOT / "generated" / "master" / "compiled"
_WORKSPACE_ROOT = Path(os.environ.get("SDD_WORKSPACE_ROOT", REPO_ROOT)).resolve()
_PROVIDENCE_COMPILED = _WORKSPACE_ROOT / ".providence" / "compiled"
FIXTURES = REPO_ROOT / "tests" / "contract" / "fixtures"

_CORE_VOLATILE_KEYS = {"fingerprint", "generated_at"}
_CLIENT_VOLATILE_KEYS = _CORE_VOLATILE_KEYS | {"fingerprint_core_salt"}

SNAPSHOTS: dict[str, dict[str, Any]] = {
    "governance": {
        "compiled": _PROVIDENCE_COMPILED / "governance-core.json",
        "golden": FIXTURES / "governance_core.golden.json",
        "volatile_keys": _CORE_VOLATILE_KEYS,
    },
    "governance-client": {
        "compiled": _PROVIDENCE_COMPILED / "governance-client.json",
        "golden": FIXTURES / "governance_client.golden.json",
        "volatile_keys": _CLIENT_VOLATILE_KEYS,
    },
}


def _normalise(
    d: dict[str, Any], volatile_keys: set[str] = _CORE_VOLATILE_KEYS
) -> dict[str, Any]:
    """Remove volatile fields, sort items by ID, and sort keys for deterministic comparison."""
    clean = {k: v for k, v in d.items() if k not in volatile_keys}
    if "items" in clean and isinstance(clean["items"], list):
        clean["items"] = sorted(clean["items"], key=lambda x: x.get("id", ""))
    return json.loads(json.dumps(clean, sort_keys=True))  # type: ignore[no-any-return]


def compile_governance() -> bool:
    """Compile governance artifacts using the project's own Python environment.

    Supports running via the 'providence' binary (if installed) or falling back to
    'python -m providence_cli' with appropriate PYTHONPATH for workspace members.
    """
    import importlib
    import os

    SafeProcessRunner = importlib.import_module(
        "providence_core.utils.process"
    ).SafeProcessRunner

    # Identify workspace source directories to support uninstalled execution
    package_roots = [
        REPO_ROOT / "packages/core/providence_core/src",
        REPO_ROOT / "packages/core/providence_telemetry/src",
        REPO_ROOT / "packages/features/providence_integration/src",
        REPO_ROOT / "packages/interfaces/providence_wizard/src",
        REPO_ROOT / "packages/interfaces/providence_cli/src",
    ]

    # Build environment with PYTHONPATH including workspace sources
    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    new_pp = os.pathsep.join([str(p) for p in package_roots])
    env["PYTHONPATH"] = f"{new_pp}{os.pathsep}{existing_pp}" if existing_pp else new_pp
    # Skip seed regeneration: golden snapshot script should only update tests/contract/fixtures
    env["SDD_SKIP_SEED_REGEN"] = "1"

    # Determine how to invoke the CLI
    providence_bin = Path(sys.executable).with_name("providence")
    providence_cmd = (
        [str(providence_bin)]
        if providence_bin.exists()
        else [sys.executable, "-m", "providence_cli"]
    )

    print("Compiling governance artifacts...")
    result_comp = SafeProcessRunner().run(
        providence_cmd + ["governance", "compile"],
        cwd=REPO_ROOT,
        capture_output=True,
        env=env,
    )
    if result_comp.returncode != 0:
        print("ERROR: governance compile failed:")
        print(result_comp.stdout)
        print(result_comp.stderr)
        return False

    print("Governance compiled successfully.")
    return True


def update_snapshot(name: str, dry_run: bool = False) -> bool:
    """Update a single golden file snapshot. Returns True on success."""
    if name not in SNAPSHOTS:
        print(f"ERROR: Unknown snapshot '{name}'. Available: {', '.join(SNAPSHOTS)}")
        return False

    compiled_path = SNAPSHOTS[name]["compiled"]
    golden_path = SNAPSHOTS[name]["golden"]
    volatile_keys = SNAPSHOTS[name].get("volatile_keys", _CORE_VOLATILE_KEYS)

    if not compiled_path.exists():
        print(f"ERROR: Compiled artifact not found: {compiled_path}")
        print("       Run: uv run providence governance compile")
        return False

    normalised = _normalise(json.loads(read_text_utf8(compiled_path)), volatile_keys)
    new_content = json.dumps(normalised, indent=2, sort_keys=True) + "\n"

    # Detect no-change and build diff baseline
    old_lines: list[str] = []
    if golden_path.exists():
        current = json.loads(read_text_utf8(golden_path))
        if current == normalised:
            print(f"No change: {golden_path.name} is already up to date.")
            return True
        old_lines = json.dumps(current, indent=2, sort_keys=True).splitlines(
            keepends=True
        )

    # Show diff
    new_lines = json.dumps(normalised, indent=2, sort_keys=True).splitlines(
        keepends=True
    )
    diff = "".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="golden (before)",
            tofile="golden (after)",
            n=3,
        )
    )
    print(f"\n--- diff for {golden_path.name} ---")
    print(diff or "(new file)")

    if dry_run:
        print(f"[DRY RUN] Would write {len(new_content)} bytes to {golden_path}")
        return True

    golden_path.parent.mkdir(parents=True, exist_ok=True)
    write_text_utf8(golden_path, new_content)
    print(f"Updated: {golden_path}")
    return True


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Update golden-file snapshots for contract tests.",
        epilog="Tip: use 'make update-golden-snapshots' as the canonical entry point.",
    )
    parser.add_argument(
        "snapshot",
        nargs="?",
        default=None,
        help=f"Snapshot to update: {', '.join(SNAPSHOTS)} (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing any files",
    )
    args = parser.parse_args()

    if not args.dry_run and not compile_governance():
        return 1

    targets = [args.snapshot] if args.snapshot else list(SNAPSHOTS.keys())
    return 0 if all(update_snapshot(t, dry_run=args.dry_run) for t in targets) else 1


if __name__ == "__main__":
    sys.exit(main())
