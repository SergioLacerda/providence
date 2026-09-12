"""Support helpers for the test command group."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import typer


def build_test_command(
    script: Path,
    *,
    verbose: bool,
    fail_fast: bool,
    coverage: bool,
    cov_fail_under: int | None,
) -> list[str]:
    cmd = [sys.executable, str(script)]
    if verbose:
        cmd.append("--verbose")
    if fail_fast:
        cmd.append("--fail-fast")
    if not coverage:
        cmd.append("--no-coverage")
    if cov_fail_under is not None:
        cmd.extend(["--cov-fail-under", str(cov_fail_under)])
    return cmd


def run_test_pipeline(cmd: list[str], *, root: Path) -> None:
    from providence_core.utils.process import (
        ProcessAuthorizationError,
        ProcessNonZeroExitError,
        ProcessSpawnError,
        ProcessTimeoutError,
        SafeProcessRunner,
    )

    typer.echo(f"Running tests from: {cmd[1]}")
    try:
        SafeProcessRunner().run(cmd, cwd=root, check=True, capture_output=False)
    except ProcessNonZeroExitError as err:
        typer.echo(f"ERROR: test pipeline failed: {err}", err=True)
        raise typer.Exit(1) from None
    except ProcessAuthorizationError as err:
        typer.echo(f"ERROR: execution blocked by policy: {err}", err=True)
        raise typer.Exit(2) from None
    except ProcessTimeoutError:
        typer.echo("ERROR: test pipeline timed out", err=True)
        raise typer.Exit(124) from None
    except ProcessSpawnError as err:
        typer.echo(f"ERROR: could not start test pipeline: {err}", err=True)
        raise typer.Exit(127) from None


def run_ci_validate(
    *,
    root: Path,
    health: bool,
    governance: bool,
    tests: bool,
    soak_threads: bool,
    check_import: Any,
    run_script: Any,
    run_cli: Any,
    run_pytest: Any,
    require_dev_module: Any,
) -> None:
    failed = False
    typer.echo("=== Import checks ===")
    for mod in [
        "yaml",
        "typer",
        "rich",
        "msgpack",
        "providence_core",
        "providence_integration",
        "providence_cli",
    ]:
        ok = check_import(mod)
        typer.echo(f"  {'PASS' if ok else 'FAIL'}: {mod}")
        if not ok:
            failed = True
    failed = _run_health(root, health, run_script, failed)
    failed = _run_governance(root, governance, run_script, run_cli, failed)
    failed = _run_tests(root, tests, run_script, require_dev_module, failed)
    if soak_threads:
        require_dev_module("pytest")
        typer.echo("\n=== Thread soak ===")
        if (
            run_pytest(
                [
                    "packages/interfaces/providence_cli/tests/test_metrics_reload_worker.py",
                    "-k",
                    "soak_restart_cycles",
                ],
                str(root),
            )
            != 0
        ):
            failed = True
    if failed:
        typer.echo("\nERROR: One or more checks failed")
        raise typer.Exit(1)
    typer.echo("\nAll checks passed")


def _run_health(root: Path, enabled: bool, run_script: Any, failed: bool) -> bool:
    if not enabled:
        return failed
    typer.echo("\n=== Health check ===")
    script = root / "tools" / "health" / "health_check.py"
    if not script.exists():
        typer.echo(f"  FAIL: not found at {script}")
        return True
    return run_script(str(script), ["--verbose"], str(root)) != 0 or failed


def _run_governance(
    root: Path, enabled: bool, run_script: Any, run_cli: Any, failed: bool
) -> bool:
    if not enabled:
        return failed
    typer.echo("\n=== Governance compliance ===")
    typer.echo("  Running governance compile...")
    if run_cli(["governance", "compile"], str(root)) != 0:
        failed = True
    typer.echo("  Running runtime status...")
    runtime_rc = run_cli(["runtime", "status", "--force"], str(root))
    if runtime_rc not in (0, 3):
        failed = True
    typer.echo("  Running governance score/adherence/validate...")
    for args in (
        ["governance", "score", "--threshold", "0"],
        ["governance", "adherence", "--threshold", "0"],
        ["governance", "validate"],
    ):
        if run_cli(args, str(root)) != 0:
            failed = True
    script = root / "tools" / "governance" / "compliance.py"
    if not script.exists():
        typer.echo(f"  FAIL: not found at {script}")
        return True
    return (
        run_script(str(script), ["--verify", "--check-integrity"], str(root)) != 0
        or failed
    )


def _run_tests(
    root: Path, enabled: bool, run_script: Any, require_dev_module: Any, failed: bool
) -> bool:
    if not enabled:
        return failed
    require_dev_module("pytest")
    typer.echo("\n=== Test suite ===")
    script = root / "tools" / "testing" / "run-all-tests.py"
    if not script.exists():
        typer.echo(f"  FAIL: not found at {script}")
        return True
    return run_script(str(script), [], str(root)) != 0 or failed
