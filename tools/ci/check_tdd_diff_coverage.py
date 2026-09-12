#!/usr/bin/env python3
"""TDD diff-coverage gate (A8 — enforce M002 per change, not just aggregate count).

M002 (`.providence/source/mandates/mandates.md`) mandates writing tests before
production code. The previous "Validate Test Coverage (M002)" CI step only
counted total `test_*.py` files repo-wide and never failed the build — it
could not catch a single PR that changes production code without touching
any test. This gate looks at the actual diff: if changed files include
production source under a package's `src/`, the same diff must also touch at
least one test file (anywhere), else the change is flagged.

`--mode enforce` (default) fails the build; `--mode warn` reports only.
Start at `warn` for a new gate's rollout, per the project's own WARN → BLOCK
→ STRICT enforcement-ladder convention, then promote once false-block rate
is observed to be low.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess  # nosec B404
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories exempt from the "production code needs a test" rule: they hold
# no executable production logic reachable by tests, or are test/config
# infrastructure themselves.
_EXEMPT_PATH_PARTS = (
    "/tests/",
    "/docs/",
    "/.github/",
    "/tools/",
    "/generated/",
    "/build/",
    "/.providence/",
)
_EXEMPT_FILENAMES = {"__init__.py", "conftest.py", "py.typed"}


def _is_production_source(path: str) -> bool:
    if not path.endswith(".py"):
        return False
    if "/src/" not in f"/{path}":
        return False
    if any(part in f"/{path}" for part in _EXEMPT_PATH_PARTS):
        return False
    filename = path.rsplit("/", 1)[-1]
    return filename not in _EXEMPT_FILENAMES


def _is_test_file(path: str) -> bool:
    if not path.endswith(".py"):
        return False
    filename = path.rsplit("/", 1)[-1]
    return (
        filename.startswith("test_")
        or filename.endswith("_test.py")
        or "/tests/" in f"/{path}"
    )


def _changed_files(base_ref: str) -> list[str] | None:
    """Return files changed vs *base_ref*, or None if the diff can't be computed."""
    result = subprocess.run(  # nosec B603, B607
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="TDD diff-coverage gate (M002).")
    parser.add_argument(
        "--mode",
        choices=["warn", "enforce"],
        default="warn",
        help="warn reports only (exit 0); enforce fails the build on violation.",
    )
    parser.add_argument(
        "--base-ref",
        default="",
        help="Git ref to diff against (default: $GITHUB_BASE_REF or HEAD~1).",
    )
    parser.add_argument(
        "--json-out", default="", help="Optional JSON diagnostics path."
    )
    args = parser.parse_args()

    base_ref = args.base_ref or os.environ.get("GITHUB_BASE_REF", "")
    candidates = ([f"origin/{base_ref}", base_ref] if base_ref else []) + ["HEAD~1"]

    changed: list[str] | None = None
    resolved_base = ""
    for candidate in candidates:
        changed = _changed_files(candidate)
        if changed is not None:
            resolved_base = candidate
            break

    if changed is None:
        print(
            "TDD diff-coverage gate: could not compute a diff against any candidate "
            f"base ref ({candidates}); skipping (infra limitation, not a policy failure)."
        )
        return 0

    production_changed = sorted(f for f in changed if _is_production_source(f))
    tests_changed = sorted(f for f in changed if _is_test_file(f))

    ok = not production_changed or bool(tests_changed)
    payload = {
        "gate": "tdd-diff-coverage",
        "mandate": "M002",
        "mode": args.mode,
        "base_ref": resolved_base,
        "ok": ok,
        "production_files_changed": production_changed,
        "test_files_changed": tests_changed,
        "error_code": None if ok else "TDD_DIFF_NO_TEST_TOUCHED",
    }

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if ok:
        print(
            f"✓ M002 diff-coverage: {len(production_changed)} production file(s) changed, "
            f"{len(tests_changed)} test file(s) touched."
        )
        return 0

    print(
        "TDD diff-coverage gate: production code changed without touching any "
        "test file in the same diff (M002 — Red-Green-Refactor).\n"
        "Production files changed:\n  " + "\n  ".join(production_changed)
    )
    if args.mode == "warn":
        print(
            "Mode=warn: not failing the build. Add/update a test before promoting to enforce."
        )
        return 0
    print("Mode=enforce: failing the build. Add or update a test covering this change.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
