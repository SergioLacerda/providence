"""Test."""

from pathlib import Path

import typer

from providence_cli.commands._test_command_support import (
    build_test_command,
    run_test_pipeline,
)
from providence_cli.commands._test_command_support import (
    run_ci_validate as _run_ci_validate,
)
from providence_cli.services.command_group_output import show_command_group
from providence_cli.services.test_handler import (
    _check_import,
    _run_cli,
    _run_pytest,
    _run_script,
    run_review_golden,
)
from providence_cli.utils.dev_deps import require_dev_module
from providence_cli.utils.environment import detect_repo_root

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List test commands."),
) -> None:
    """Run test pipeline."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Test", ["run", "ci-validate", "review-golden"])
        raise typer.Exit(0)


class TestCommand:
    """TestCommand."""

    def run(
        self,
        verbose: bool,
        fail_fast: bool,
        coverage: bool,
        cov_fail_under: int | None,
    ) -> None:
        """Run."""
        require_dev_module("pytest")
        root = detect_repo_root()
        script = root / "tools" / "testing" / "run-all-tests.py"

        if not script.exists():
            typer.echo(f"ERROR: Script not found: {script}")
            raise typer.Exit(1)
        run_test_pipeline(
            build_test_command(
                script,
                verbose=verbose,
                fail_fast=fail_fast,
                coverage=coverage,
                cov_fail_under=cov_fail_under,
            ),
            root=root,
        )


@app.command()
def run(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose pytest output"
    ),
    fail_fast: bool = typer.Option(
        False, "--fail-fast", "-x", help="Stop on first failure"
    ),
    coverage: bool = typer.Option(
        True, "--coverage/--no-coverage", help="Show project coverage summary"
    ),
    cov_fail_under: int | None = typer.Option(  # noqa: UP045
        None,
        "--cov-fail-under",
        help="Fail when coverage is below this percentage (default: 80)",
    ),
) -> None:
    """Run full test pipeline"""
    TestCommand().run(
        verbose=verbose,
        fail_fast=fail_fast,
        coverage=coverage,
        cov_fail_under=cov_fail_under,
    )


@app.command(name="ci-validate")
def ci_validate(  # noqa: C901
    health: bool = typer.Option(
        True,
        "--health/--no-health",
        help="Run health check (tools/health/health_check.py)",
    ),
    governance: bool = typer.Option(
        True,
        "--governance/--no-governance",
        help="Run governance compliance + integrity (tools/governance/compliance.py)",
    ),
    tests: bool = typer.Option(
        True,
        "--tests/--no-tests",
        help="Run full test suite (tools/testing/run-all-tests.py)",
    ),
    soak_threads: bool = typer.Option(
        False,
        "--soak-threads/--no-soak-threads",
        help="Run slow thread lifecycle soak test for metrics service",
    ),
) -> None:
    """Preflight CI validation: import checks + CI-like governance + tests."""
    _run_ci_validate(
        root=detect_repo_root(),
        health=health,
        governance=governance,
        tests=tests,
        soak_threads=soak_threads,
        check_import=_check_import,
        run_script=_run_script,
        run_cli=_run_cli,
        run_pytest=_run_pytest,
        require_dev_module=require_dev_module,
    )


@app.command(name="review-golden")
def review_golden(
    update: bool = typer.Option(
        False,
        "--update",
        help="Update the golden snapshot with the current artifact.",
    ),
    fail_on_breaking: bool = typer.Option(
        True,
        "--fail-on-breaking/--no-fail-on-breaking",
        help="Exit 1 when breaking changes are detected (default: true).",
    ),
    artifact: Path = typer.Option(  # noqa: B008
        None,
        "--artifact",
        help="Path to governance-core.json artifact (auto-detected if omitted).",
    ),
    golden: Path = typer.Option(  # noqa: B008
        None,
        "--golden",
        help="Path to golden snapshot JSON (default: .providence/runtime/golden-ast.json).",
    ),
) -> None:
    """Compare current compiled artifact against the golden AST snapshot.

    On first run (no snapshot yet) the current artifact is saved as the golden
    baseline and the command exits 0.  On subsequent runs the diff is reported
    and the command exits 1 when breaking changes are found (unless
    --no-fail-on-breaking is set).

    Use --update to refresh the golden baseline intentionally.
    """
    run_review_golden(
        root=detect_repo_root(),
        update=update,
        fail_on_breaking=fail_on_breaking,
        artifact=artifact,
        golden=golden,
    )
