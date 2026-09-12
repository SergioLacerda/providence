#!/usr/bin/env python3
# /// script
# dependencies = ["ruff"]
# ///
"""Lint all Providence packages and tools across the monorepo."""

import argparse
import io
import sys
from pathlib import Path

if sys.platform == "win32":
    # Windows consoles default to the legacy codepage (e.g. cp1252), which
    # can't encode the emoji used in status output below.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")

# Repo root is two levels up from tools/maintenance/
REPO_ROOT = Path(__file__).resolve().parents[2]
_PROVIDENCE_CORE_SRC = REPO_ROOT / "packages" / "core" / "providence_core" / "src"
if str(_PROVIDENCE_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(_PROVIDENCE_CORE_SRC))

LINT_LAYERS = [
    ("Packages: Core", "packages/core"),
    ("Packages: Features", "packages/features"),
    ("Packages: Interfaces", "packages/interfaces"),
    ("Tools", "tools"),
    ("Tests", "tests"),
]


def run_step(name: str, cmd: list[str]) -> bool:
    """Run a linting step and return True if successful."""
    from providence_core.utils.process import SafeProcessRunner

    print(f"\n--- {name} ---")
    result = SafeProcessRunner().run(cmd, cwd=REPO_ROOT, capture_output=False)
    return result.returncode == 0


def _run_ruff_steps(
    layers: list[tuple[str, str]],
    ruff_base: list[str],
    fmt_base: list[str],
    check_only: bool,
) -> bool:
    """Run Ruff check and format steps."""
    passed = True
    for name, path in layers:
        target = REPO_ROOT / path
        if target.exists() and not run_step(
            f"Ruff Check: {name}", ruff_base + [str(target)]
        ):
            passed = False

    if not check_only:
        for name, path in layers:
            target = REPO_ROOT / path
            if target.exists() and not run_step(
                f"Ruff Format: {name}", fmt_base + [str(target)]
            ):
                passed = False
    return passed


def _run_arch_steps() -> bool:
    """Run architecture validation tools."""
    passed = True
    arch_steps: list[tuple[str, list[str]]] = [
        (
            "tools/architecture/validate_imports.py",
            [sys.executable, "tools/architecture/validate_imports.py"],
        ),
        (
            "tools/architecture/validate_import_style.py",
            [sys.executable, "tools/architecture/validate_import_style.py"],
        ),
        (
            "tools/architecture/validate_cycles.py",
            [sys.executable, "tools/architecture/validate_cycles.py"],
        ),
        (
            "tools/architecture/validate_class_size.py",
            [
                sys.executable,
                "tools/architecture/validate_class_size.py",
                "--show-module-warnings",
            ],
        ),
    ]
    for tool, cmd in arch_steps:
        if (REPO_ROOT / tool).exists() and not run_step(f"Arch: {tool}", cmd):
            passed = False
    return passed


def _run_mypy_step(layer_filter: str | None) -> bool:
    """Run MyPy type check."""
    # SIM103: Return the negated condition directly
    return not (
        (not layer_filter or "packages" in layer_filter.lower())
        and not run_step("MyPy Type Check", [sys.executable, "-m", "mypy", "."])
    )


def _run_bandit_step(layer_filter: str | None) -> bool:
    """Run Bandit security scan."""
    # SIM103: Return the negated condition directly
    return not (
        (not layer_filter or "packages" in layer_filter.lower())
        and not run_step(
            "Bandit Security Scan",
            [
                sys.executable,
                "-m",
                "bandit",
                "-r",
                "packages/",
                "-c",
                "pyproject.toml",
                "--severity-level",
                "medium",
                "--confidence-level",
                "medium",
                "-q",
            ],
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint the Providence monorepo")
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues")
    parser.add_argument(
        "--check-only", action="store_true", help="Only check, no format"
    )
    parser.add_argument("--layer", help="Filter by layer name")
    args = parser.parse_args()

    all_passed = True

    # 1 & 2. Ruff
    ruff_base = [sys.executable, "-m", "ruff", "check"]
    if args.fix:
        ruff_base.append("--fix")

    fmt_base = [sys.executable, "-m", "ruff", "format"]
    if not args.fix:
        fmt_base.append("--check")

    layers_to_run = LINT_LAYERS
    if args.layer:
        layers_to_run = [
            layer_item
            for layer_item in LINT_LAYERS
            if args.layer.lower() in layer_item[0].lower()
        ]

    if not _run_ruff_steps(layers_to_run, ruff_base, fmt_base, args.check_only):
        all_passed = False

    # 3. Architecture
    if not args.layer and not _run_arch_steps():
        all_passed = False

    # 4. MyPy
    if not _run_mypy_step(args.layer):
        all_passed = False

    # 5. Bandit
    if not _run_bandit_step(args.layer):
        all_passed = False

    if all_passed:
        print("\n✅ LINT PASSED")
        return 0
    else:
        print("\n❌ LINT FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
