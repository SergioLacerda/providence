"""Lint."""

import sys

import typer

from providence_cli.services.command_group_output import show_command_group
from providence_cli.services.lint_handler import (
    _check_legacy_patterns,
    _check_project_leaks,
    _collect_active_markdown_files,  # noqa: F401  backward-compat re-export for unit tests
    _collect_anchor_files,
    _extract_file_anchors,  # noqa: F401  backward-compat re-export for unit tests
    _filter_code_blocks,  # noqa: F401  backward-compat re-export for unit tests
    _resolve_link_target,  # noqa: F401  backward-compat re-export for unit tests
    _slugify_anchor,  # noqa: F401  backward-compat re-export for unit tests
    _validate_anchor_style,
    _validate_link_fragment_style,  # noqa: F401  backward-compat re-export for unit tests
    _validate_markdown_anchors,
)
from providence_cli.utils.command_errors import handle_cli_errors

__all__ = [
    "_collect_active_markdown_files",
    "_extract_file_anchors",
    "_filter_code_blocks",
    "_resolve_link_target",
    "_slugify_anchor",
    "_validate_link_fragment_style",
]

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List lint commands."),
) -> None:
    """Run lint checks."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Lint", ["spec", "run"])
        raise typer.Exit(0)


def _run_step(label: str, cmd: list[str], *, fix: bool) -> int:
    from providence_core.utils.process import SafeProcessRunner

    runner = SafeProcessRunner()

    typer.echo(f"\nRunning: {label}")
    result = runner.run(cmd)
    if not result.success:
        if fix:
            typer.echo(f"  WARN: {label} reported issues (auto-fix attempted)")
        else:
            typer.echo(f"  ERROR: {label} failed")
    else:
        typer.echo(f"  OK: {label} OK")
    return result.returncode


def _run_ruff(fix: bool) -> bool:
    """Run ruff check + format. Returns True if anything failed (unfixed)."""
    from providence_cli.utils.dev_deps import require_dev_module

    require_dev_module("ruff")

    ruff_cmd = [sys.executable, "-m", "ruff", "check", "."]
    if fix:
        ruff_cmd += ["--fix", "--unsafe-fixes"]
    check_failed = _run_step("ruff", ruff_cmd, fix=fix) != 0 and not fix
    if check_failed:
        typer.echo(
            "  HINT: Ruff includes F401 (unused imports). Remove dead imports or move type-only imports under TYPE_CHECKING."
        )

    fmt_cmd = [sys.executable, "-m", "ruff", "format", "."]
    if not fix:
        fmt_cmd.append("--check")
    fmt_failed = _run_step("ruff format", fmt_cmd, fix=fix) != 0 and not fix

    return check_failed or fmt_failed


@app.command()
def spec(
    validate_all_anchors: bool = typer.Option(
        True,
        "--validate-all-anchors/--validate-entry-anchors",
        help="Validate anchors on all active documentation files (excluding docs/archive)",
    ),
    strict_anchor_style: bool = typer.Option(
        True,
        "--strict-anchor-style/--no-strict-anchor-style",
        help="Fail on fragile anchor patterns such as URL-encoded fragments",
    ),
) -> None:
    """Check documentation structure and canonical paths."""
    from providence_cli.utils.environment import detect_repo_root

    repo_root = detect_repo_root()
    canonical_dir = repo_root / "docs" / "spec" / "canonical"

    if not canonical_dir.exists():
        typer.echo(f"  ERROR: Canonical directory not found: {canonical_dir}")
        raise typer.Exit(1)

    typer.echo(f" Checking canonical documentation in {canonical_dir}...")
    errors = _check_legacy_patterns(canonical_dir, repo_root)
    errors += _check_project_leaks(canonical_dir, repo_root)

    anchor_files = _collect_anchor_files(repo_root, validate_all_anchors)
    if anchor_files:
        errors += _validate_markdown_anchors(anchor_files, repo_root)
        if strict_anchor_style:
            errors += _validate_anchor_style(anchor_files, repo_root)

    if errors > 0:
        typer.echo(f"\n Spec linting failed with {errors} errors")
        raise typer.Exit(1)

    typer.echo(" Spec structure OK")


@app.command()
@handle_cli_errors(command_name="lint run")
def run(
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Auto-fix ruff lint and format issues (includes unsafe fixes)",
    ),
    skip_mypy: bool = typer.Option(
        False, "--skip-mypy", help="Skip mypy type checking"
    ),
    skip_bandit: bool = typer.Option(
        False, "--skip-bandit", help="Skip bandit security checks"
    ),
    skip_spec: bool = typer.Option(
        False, "--skip-spec", help="Skip spec structure linting"
    ),
) -> None:
    """Run all lint checks: ruff, architecture, mypy, bandit, spec."""
    failed = _run_ruff(fix)

    architecture_checks = [
        (
            "architecture imports",
            [sys.executable, "tools/architecture/validate_imports.py"],
        ),
        (
            "architecture cycles",
            [sys.executable, "tools/architecture/validate_cycles.py"],
        ),
        (
            "architecture class-size",
            [
                sys.executable,
                "tools/architecture/validate_class_size.py",
                "--show-module-warnings",
            ],
        ),
        (
            "cognitive governance",
            [sys.executable, "tools/governance/validate_cognitive_governance.py"],
        ),
    ]
    for label, cmd in architecture_checks:
        if _run_step(label, cmd, fix=False) != 0:
            failed = True

    if not skip_mypy:
        from providence_cli.utils.dev_deps import require_dev_module

        require_dev_module("mypy")
        if _run_step("mypy", [sys.executable, "-m", "mypy", "."], fix=False) != 0:
            failed = True

    if not skip_bandit:
        from providence_cli.utils.dev_deps import require_dev_module

        require_dev_module("bandit")
        bandit_cmd = [sys.executable, "-m", "bandit", "-r", "packages/", "-ll", "-q"]
        if _run_step("bandit", bandit_cmd, fix=False) != 0:
            failed = True

    if not skip_spec:
        spec()

    if failed:
        raise typer.Exit(1)
