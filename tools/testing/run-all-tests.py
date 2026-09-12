#!/usr/bin/env python3
# /// script
# dependencies = [
#   "pytest",
#   "pytest-asyncio",
#   "pytest-cov",
#   "coverage",
#   "pytest-xdist",
#   "pytest-timeout",
#   "msgpack",
#   "PyYAML",
#   "typer",
#   "rich",
#   "python-dotenv",
#   "pydantic",
# ]
# ///
"""Run all Providence tests across all layers of the monorepo."""

import argparse
import json
import multiprocessing
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Repo root is two levels up from tools/testing/
REPO_ROOT = Path(__file__).resolve().parents[2]
_PROVIDENCE_CORE_SRC = REPO_ROOT / "packages" / "core" / "providence_core" / "src"
_PROVIDENCE_RUNTIME_SRC = REPO_ROOT / "packages" / "core" / "providence_runtime" / "src"
_PROVIDENCE_TELEMETRY_SRC = (
    REPO_ROOT / "packages" / "core" / "providence_telemetry" / "src"
)
if str(_PROVIDENCE_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(_PROVIDENCE_CORE_SRC))
if str(_PROVIDENCE_RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(_PROVIDENCE_RUNTIME_SRC))

# Every workspace member's src/, mirroring pyproject.toml's
# [tool.pytest.ini_options].pythonpath. Each per-package layer below invokes
# pytest as its own subprocess against a single package's tests/ subdirectory
# — pytest's config-file discovery then walks upward from *that* path and
# can land on the package's own, pythonpath-less pyproject.toml (every
# workspace member has one) instead of this root one, before ever reaching
# this file. That silently drops the pythonpath list and breaks
# sibling-package imports (e.g. providence_cli's tests importing providence_runtime) in any
# environment where the workspace members aren't also editable-installed
# (e.g. a plain `uv sync` at the repo root, which only installs shared dev
# dependencies — no workspace member is a dependency of the root project
# itself). Setting PYTHONPATH directly on each subprocess sidesteps pytest's
# config discovery entirely, so it works regardless of which pyproject.toml
# pytest resolves.
_WORKSPACE_SRC_DIRS = [
    REPO_ROOT,
    REPO_ROOT / "packages" / "core" / "providence_core" / "src",
    REPO_ROOT / "packages" / "core" / "providence_runtime" / "src",
    REPO_ROOT / "packages" / "core" / "providence_telemetry" / "src",
    REPO_ROOT / "packages" / "features" / "providence_integration" / "src",
    REPO_ROOT / "packages" / "features" / "providence_adapters" / "src",
    REPO_ROOT / "packages" / "features" / "providence_skills" / "src",
    REPO_ROOT / "packages" / "features" / "providence_pages" / "src",
    REPO_ROOT / "packages" / "interfaces" / "providence_wizard" / "src",
    REPO_ROOT / "packages" / "interfaces" / "providence_cli" / "src",
]
if str(_PROVIDENCE_TELEMETRY_SRC) not in sys.path:
    sys.path.insert(0, str(_PROVIDENCE_TELEMETRY_SRC))


@dataclass
class TestLayer:
    name: str
    path: str
    description: str


# Actual test directories as they exist in this monorepo.
# Paths are relative to REPO_ROOT.
TEST_LAYERS = [
    TestLayer(
        "Package: providence_core",
        "packages/core/providence_core/tests",
        "Core package tests",
    ),
    TestLayer(
        "Package: providence_runtime",
        "packages/core/providence_runtime/tests",
        "Runtime tests",
    ),
    TestLayer(
        "Package: providence_telemetry",
        "packages/core/providence_telemetry/tests",
        "Telemetry tests",
    ),
    TestLayer(
        "Package: providence_adapters",
        "packages/features/providence_adapters/tests",
        "Adapter generation tests",
    ),
    TestLayer(
        "Package: providence_integration",
        "packages/features/providence_integration/tests",
        "Integration tests",
    ),
    TestLayer(
        "Package: providence_skills",
        "packages/features/providence_skills/tests",
        "Skill contract tests",
    ),
    TestLayer(
        "Package: providence_wizard",
        "packages/interfaces/providence_wizard/tests",
        "Wizard UI/Logic tests",
    ),
    TestLayer(
        "Package: providence_cli",
        "packages/interfaces/providence_cli/tests",
        "CLI Interface tests",
    ),
    TestLayer("Layer: Unit", "tests/unit", "Global unit tests"),
    TestLayer("Layer: Integration", "tests/integration", "Global integration tests"),
    TestLayer("Layer: Contract", "tests/contract", "Architectural contract tests"),
]


def _run_governed(
    cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None
) -> int:
    from providence_core.utils.process import SafeProcessRunner

    runner = SafeProcessRunner()
    result = runner.run(cmd, capture_output=False, cwd=cwd or REPO_ROOT, env=env)
    return result.returncode


def run_layer(
    layer: TestLayer,
    verbose: bool = False,
    fail_fast: bool = False,
    coverage: bool = False,
    parallel: bool = True,
    extra_args: list[str] | None = None,
    max_workers: int = 2,
) -> tuple[bool, str]:
    """Run pytest for one layer. Returns (success, summary_line)."""
    layer_path = REPO_ROOT / layer.path

    if not layer_path.exists():
        return True, f"SKIP  {layer.name}: directory not found ({layer.path})"

    print(f"\n{'=' * 70}")
    print(f"LAYER: {layer.name} — {layer.description}")
    print(f"PATH:  {layer_path}")
    print("=" * 70)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(layer_path),
        "--tb=long" if os.environ.get("CI") else "--tb=short",
        "-v" if verbose else "-q",
        "--durations=5",  # Show 5 slowest tests
    ]

    if parallel and not os.environ.get("CI"):
        # Check for xdist availability to avoid "unrecognized argument: -n"
        has_xdist = False
        try:
            import xdist  # type: ignore[import-untyped]  # noqa: F401

            has_xdist = True
        except ImportError:
            # Backward compatibility for environments exposing legacy module name.
            try:
                import pytest_xdist  # noqa: F401

                has_xdist = True
            except ImportError:
                # pytest-xdist not installed, will run tests sequentially
                pass

        if has_xdist:
            # Cap workers to avoid saturating the machine on local dev.
            # CI can raise this via --max-workers, but local default is 2.
            cpus = min(max(1, multiprocessing.cpu_count() - 1), max_workers)
            if cpus > 1:
                cmd += ["-n", str(cpus)]
        else:
            print(
                f"  ⚠️  pytest-xdist not found, falling back to sequential execution for {layer.name}"
            )

    if fail_fast:
        cmd.append("-x")

    layer_env = os.environ.copy()
    workspace_pythonpath = os.pathsep.join(str(p) for p in _WORKSPACE_SRC_DIRS)
    existing_pythonpath = layer_env.get("PYTHONPATH", "")
    layer_env["PYTHONPATH"] = (
        f"{workspace_pythonpath}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else workspace_pythonpath
    )
    if coverage:
        # Use one coverage data file per layer run to avoid SQLite write collisions.
        layer_slug = layer.path.replace("/", "_")
        layer_env["COVERAGE_FILE"] = str(REPO_ROOT / f"build/.coverage.{layer_slug}")
        cmd += [
            "--cov=packages",
            # Keep per-layer runs quiet; enforce coverage gate only once at end.
            "--cov-report=",
            "--cov-fail-under=0",
        ]

    if extra_args:
        cmd += extra_args

    result_code = _run_governed(cmd, cwd=REPO_ROOT, env=layer_env)
    success = result_code == 0
    status = "PASS" if success else "FAIL"
    print(f"\n{status}: {layer.name}")
    return success, f"{status:4}  {layer.name}"


def _print_layers() -> int:
    """Print available test layers and return 0."""
    print("\nAvailable test layers:\n")
    for i, layer in enumerate(TEST_LAYERS, 1):
        exists = "✓" if (REPO_ROOT / layer.path).exists() else "✗ (missing)"
        print(f"  {i}. {layer.name:30} {exists}")
        print(f"     {layer.description}")
        print(f"     {layer.path}\n")
    return 0


def _report_coverage(fail_under: int) -> bool:
    """Run coverage report; return True if threshold is met."""
    print(f"\n{'=' * 70}")
    print("FINAL COVERAGE REPORT (Aggregated)")
    print("=" * 70)

    combine_code = _run_governed(
        [
            sys.executable,
            "-m",
            "coverage",
            "combine",
            "build",
        ],
        cwd=REPO_ROOT,
    )
    if combine_code != 0:
        return False

    result_code = _run_governed(
        [
            sys.executable,
            "-m",
            "coverage",
            "report",
            "--format=total",
            f"--fail-under={fail_under}",
        ],
        cwd=REPO_ROOT,
    )
    return result_code == 0


def _print_worst_coverage_files(top_n: int) -> None:
    """Print Top-N files with worst line coverage percentages."""
    payload = _load_coverage_files_payload()
    if payload is None:
        print("WARN: Could not compute worst-coverage file list.")
        return
    files = payload.get("files", {})
    if not isinstance(files, dict):
        print("WARN: Coverage JSON missing file data.")
        return

    rows: list[tuple[str, float, int, int]] = []
    for file_path, file_data in files.items():
        if not isinstance(file_path, str) or not isinstance(file_data, dict):
            continue
        summary = file_data.get("summary", {})
        if not isinstance(summary, dict):
            continue
        statements = int(summary.get("num_statements", 0) or 0)
        covered = int(summary.get("covered_lines", 0) or 0)
        if statements <= 0:
            continue
        pct = covered / statements * 100.0
        rows.append((file_path, pct, covered, statements))

    if not rows:
        print("Top coverage offenders: no file data.")
        return

    # Worst first by coverage %, tie-break by larger statement count then path.
    rows.sort(key=lambda x: (x[1], -x[3], x[0]))
    print(f"\nTop {top_n} Coverage Offenders (files)")
    print("=" * 70)
    for file_path, pct, covered, statements in rows[:top_n]:
        print(f"  {pct:6.2f}%  ({covered:4}/{statements:4})  {file_path}")


def _load_coverage_files_payload() -> dict[str, object] | None:
    """Export and load coverage JSON payload."""
    out_json = REPO_ROOT / "build" / "coverage-by-file.json"
    export_code = _run_governed(
        [
            sys.executable,
            "-m",
            "coverage",
            "json",
            "-o",
            str(out_json),
        ],
        cwd=REPO_ROOT,
    )
    if export_code != 0 or not out_json.exists():
        return None

    try:
        payload = json.loads(out_json.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _group_coverage_by_package(files: dict[str, object]) -> dict[str, dict[str, int]]:
    grouped: dict[str, dict[str, int]] = {}
    for file_path, file_data in files.items():
        if not isinstance(file_path, str) or not isinstance(file_data, dict):
            continue
        if not file_path.startswith("packages/"):
            continue
        parts = file_path.split("/")
        if len(parts) < 3:
            continue
        group = "/".join(parts[:3])  # e.g. packages/core/providence_runtime
        summary = file_data.get("summary", {})
        if not isinstance(summary, dict):
            continue
        statements = int(summary.get("num_statements", 0) or 0)
        covered = int(summary.get("covered_lines", 0) or 0)
        bucket = grouped.setdefault(group, {"statements": 0, "covered": 0})
        bucket["statements"] += statements
        bucket["covered"] += covered
    return grouped


def _print_grouped_coverage_summary() -> None:
    """Print grouped coverage summary by package directory."""
    payload = _load_coverage_files_payload()
    if payload is None:
        print("WARN: Could not generate grouped coverage summary.")
        return
    files = payload.get("files", {})
    if not isinstance(files, dict):
        print("WARN: Coverage JSON missing file data.")
        return

    grouped = _group_coverage_by_package(files)
    if not grouped:
        print("Grouped coverage: no package entries found.")
        return

    print("\nGrouped Coverage (by package)")
    print("=" * 70)
    rows: list[tuple[str, float, int, int]] = []
    for group, stats in grouped.items():
        statements = stats["statements"]
        covered = stats["covered"]
        pct = (covered / statements * 100.0) if statements else 0.0
        rows.append((group, pct, covered, statements))
    rows.sort(key=lambda x: x[0])
    for group, pct, covered, statements in rows:
        print(f"  {group:40} {pct:6.2f}% ({covered}/{statements})")


def _parse_extra_args() -> tuple[list[str], list[str]]:
    """Split extra args (after --) from main args."""
    main_args = sys.argv[1:]
    extra_pytest_args = []
    if "--" in main_args:
        idx = main_args.index("--")
        extra_pytest_args = main_args[idx + 1 :]
        main_args = main_args[:idx]
    return main_args, extra_pytest_args


def _prepare_coverage(coverage: bool) -> None:
    """Reset coverage data at the start of a full run."""
    if coverage:
        for cov_file in (REPO_ROOT / "build").glob(".coverage*"):
            if cov_file.is_file():
                cov_file.unlink()


def _run_layers_loop(
    layers: list[TestLayer],
    args: argparse.Namespace,
    coverage: bool,
    parallel: bool,
    extra_pytest_args: list[str],
    max_workers: int = 2,
) -> tuple[bool, list[tuple[bool, str]]]:
    """Run tests for all selected layers and return results."""
    results = []
    all_passed = True
    for layer in layers:
        success, summary = run_layer(
            layer,
            args.verbose,
            args.fail_fast,
            coverage,
            parallel,
            extra_pytest_args,
            max_workers=max_workers,
        )
        results.append((success, summary))
        all_passed = all_passed and success
        if not success and args.fail_fast:
            break
    return all_passed, results


def main() -> int:
    main_args, extra_pytest_args = _parse_extra_args()

    parser = argparse.ArgumentParser(
        description="Run all Providence tests across the monorepo"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show each test")
    parser.add_argument(
        "-x", "--fail-fast", action="store_true", help="Stop at first failure"
    )
    parser.add_argument("-l", "--layer", help="Run only layers matching this string")
    parser.add_argument(
        "--list-layers", action="store_true", help="List available layers"
    )
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage")
    parser.add_argument(
        "--no-parallel", action="store_true", help="Disable parallel execution"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=2,
        help="Max xdist workers per layer in local dev (default: 2). CI ignores this.",
    )
    parser.add_argument(
        "--cov-fail-under", type=int, default=80, help="Coverage threshold"
    )
    parser.add_argument(
        "--coverage-top",
        type=int,
        default=12,
        help="Number of worst-covered files to show in final summary",
    )
    parser.add_argument(
        "--group",
        action="store_true",
        help="Show grouped coverage summary by package after final coverage gate",
    )

    args = parser.parse_args(main_args)

    if args.list_layers:
        return _print_layers()

    coverage = not args.no_coverage
    parallel = not args.no_parallel

    _prepare_coverage(coverage)

    layers = TEST_LAYERS
    if args.layer:
        layers = [lay for lay in TEST_LAYERS if args.layer.lower() in lay.name.lower()]
        if not layers:
            print(f"ERROR: No layer matching '{args.layer}'.")
            return 1

    print(f"\n{'=' * 70}")
    print(f"Providence Test Runner — {len(layers)} layer(s)")
    if parallel:
        print("Parallel execution enabled (pytest-xdist)")
    print("=" * 70)

    all_passed, results = _run_layers_loop(
        layers,
        args,
        coverage,
        parallel,
        extra_pytest_args,
        max_workers=args.max_workers,
    )

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print("=" * 70)
    for _, summary in results:
        print(f"  {summary}")

    passed = sum(1 for s, _ in results if s)
    print(f"\n  {passed}/{len(results)} layers passed")

    if coverage and results:
        coverage_ok = _report_coverage(args.cov_fail_under)
        all_passed = all_passed and coverage_ok
        _print_worst_coverage_files(max(1, args.coverage_top))
        if args.group:
            _print_grouped_coverage_summary()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
