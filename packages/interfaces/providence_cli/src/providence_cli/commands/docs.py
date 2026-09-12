"""Docs."""

import shutil
from pathlib import Path

import click
import typer

from providence_cli.services.command_group_output import show_command_group
from providence_cli.services.governance_docs_drift import validate_governance_sources
from providence_cli.services.governance_docs_handbook_gen import (
    generate_runtime_handbook,
)
from providence_cli.services.governance_docs_handbook_lookup import (
    lookup_runtime_handbook,
)

app = typer.Typer(help="Documentation commands", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List docs commands."),
) -> None:
    """Documentation operations."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group(
            "Documentation",
            [
                "deploy",
                "validate-governance-sources",
                "generate-handbook",
                "lookup-handbook",
            ],
        )
        raise typer.Exit(0)


@app.command("deploy")
def deploy(force: bool = typer.Option(True, help="Force deploy to gh-pages")) -> None:
    """Deploy MkDocs documentation if mkdocs config exists."""
    config_files = ["mkdocs.yml", "mkdocs.yaml"]
    if not any(__import__("pathlib").Path(cfg).exists() for cfg in config_files):
        typer.echo(
            "No mkdocs config found (mkdocs.yml/mkdocs.yaml). Skipping docs deploy."
        )
        return

    if shutil.which("mkdocs") is None:
        typer.echo(
            "ERROR: mkdocs command not found. Install with: pip install mkdocs mkdocs-material"
        )
        raise click.exceptions.Exit(1)

    from providence_core.utils.process import (
        AUTHORIZED_BINARIES,
        ProcessAuthorizationError,
        ProcessNonZeroExitError,
        ProcessSpawnError,
        ProcessTimeoutError,
        SafeProcessRunner,
    )

    cmd = ["mkdocs", "gh-deploy"]
    if force:
        cmd.append("--force")

    try:
        runner = SafeProcessRunner(authorized_binaries=AUTHORIZED_BINARIES | {"mkdocs"})
        runner.run(cmd, check=True, capture_output=False)
    except ProcessNonZeroExitError as err:
        typer.echo(f"ERROR: docs deploy failed: {err}", err=True)
        raise click.exceptions.Exit(1) from None
    except ProcessAuthorizationError as err:
        typer.echo(f"ERROR: execution blocked by policy: {err}", err=True)
        raise click.exceptions.Exit(2) from None
    except ProcessTimeoutError:
        typer.echo("ERROR: docs deploy timed out", err=True)
        raise click.exceptions.Exit(124) from None
    except ProcessSpawnError as err:
        typer.echo(f"ERROR: could not start docs deploy: {err}", err=True)
        raise click.exceptions.Exit(127) from None


@app.command("validate-governance-sources")
def validate_sources() -> None:
    """Validate docs/ governance source registry against runtime artifacts."""
    report = validate_governance_sources(Path.cwd())
    typer.echo(
        "docs governance sources: "
        f"mandates={len(report.mandate_ids)} "
        f"guidelines={len(report.guideline_ids)} "
        f"handbook={len(report.handbook_ids)}"
    )
    for warning in report.warnings:
        typer.echo(f"WARN: {warning}")
    if not report.ok:
        for error in report.errors:
            typer.echo(f"ERROR: {error}", err=True)
        raise click.exceptions.Exit(1)
    typer.echo("docs governance sources validated")


@app.command("generate-handbook")
def generate_handbook() -> None:
    """Generate runtime handbook slices from classified docs/ sources."""
    report = validate_governance_sources(Path.cwd())
    if not report.ok:
        for error in report.errors:
            typer.echo(f"ERROR: {error}", err=True)
        raise click.exceptions.Exit(1)
    written = generate_runtime_handbook(Path.cwd())
    typer.echo(f"runtime handbook generated: {len(written)} files")
    for path in written:
        typer.echo(f"  {path.relative_to(Path.cwd())}")


@app.command("lookup-handbook")
def lookup_handbook(
    task_type: str | None = typer.Option(
        None, "--task-type", help="Task type to match, for example planning."
    ),
    mandate_ref: list[str] | None = typer.Option(
        None, "--mandate-ref", help="Mandate reference to match; repeatable."
    ),
    operation_phase: str | None = typer.Option(
        None, "--operation-phase", help="Operation phase to match."
    ),
    risk_level: str | None = typer.Option(
        None, "--risk-level", help="Risk level to match when entries declare it."
    ),
) -> None:
    """Lookup generated runtime handbook entries without scanning docs/."""
    report = lookup_runtime_handbook(
        Path.cwd(),
        task_type=task_type,
        mandate_refs=mandate_ref or [],
        operation_phase=operation_phase,
        risk_level=risk_level,
    )
    typer.echo(f"runtime handbook lookup: {report.diagnostic}")
    if report.status in {"missing", "invalid"}:
        raise click.exceptions.Exit(1)
    for match in report.matches:
        typer.echo(
            "  "
            f"{match['id']} "
            f"source={match['source_doc']} "
            f"runtime={match['runtime_doc']}"
        )
