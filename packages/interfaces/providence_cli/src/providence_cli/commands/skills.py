"""Skill layer commands for capability-oriented operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import click
import typer
from providence_runtime import SkillEngine

from providence_cli.commands._skills_command_support import (
    emit_pipeline_required,
    emit_skill_description,
    emit_skill_run_result,
    emit_skills_export,
    emit_skills_list,
)
from providence_cli.commands.skills_learning import app as _learning_app
from providence_cli.services.command_group_output import show_command_group
from providence_cli.services.skills_bootstrap import (
    handle_adapter_error,
    run_reconcile,
    validate_and_load_governance,
)
from providence_cli.services.skills_bootstrap import (
    run_full_bootstrap as _run_full_bootstrap_service,
)
from providence_cli.services.skills_output import emit_skills_json as _emit_skills_json
from providence_cli.services.skills_registry import (
    export_skills_payload,
    get_skill,
    list_skills,
)
from providence_cli.services.skills_resolver import (
    _generate_adapters,  # noqa: F401  backward-compat re-export for unit tests
    _read_registry_ids,  # noqa: F401  backward-compat re-export for unit tests
    _reconcile_root_seed_artifacts,  # noqa: F401  backward-compat re-export for unit tests
)
from providence_cli.shared.constants import TRUE_VALUES as _TRUE_VALUES
from providence_cli.utils.output import is_json_mode
from providence_cli.utils.providence_authority import resolve_workspace_root

__all__ = ["_generate_adapters", "_read_registry_ids", "_reconcile_root_seed_artifacts"]

app = typer.Typer(help="Capability-oriented skill commands")
app.registered_commands.extend(_learning_app.registered_commands)


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


def _validate_and_load_governance(compiled_path: Path) -> dict[str, Any]:
    return validate_and_load_governance(
        compiled_path, output_json=_ctx_json(), emit_fn=_emit_skills_json
    )


def _handle_adapter_error(adapter_error: str) -> None:
    handle_adapter_error(
        adapter_error, output_json=_ctx_json(), emit_fn=_emit_skills_json
    )


def _run_reconcile(output_base: Path, *, dry_run: bool) -> tuple[int, int]:
    return run_reconcile(
        output_base, dry_run=dry_run, output_json=_ctx_json(), emit_fn=_emit_skills_json
    )


def _run_full_bootstrap(
    *, regenerate_seeds: bool = False, dry_run: bool = False
) -> None:
    ws_root = resolve_workspace_root()
    _run_full_bootstrap_service(
        ws_root,
        regenerate_seeds=regenerate_seeds,
        dry_run=dry_run,
        output_json=_ctx_json(),
        emit_fn=_emit_skills_json,
    )


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List skill commands."),
    full_bootstrap: bool = typer.Option(
        False,
        "--full-bootstrap",
        help=(
            "Generate all available skills/commands/seeds artifacts from canonical "
            ".providence governance data."
        ),
    ),
    regenerate_seeds: bool = typer.Option(
        False,
        "--regenerate-seeds",
        help=(
            "Regenerate and reconcile root seed artifacts from canonical "
            ".providence command/skill registries (deletes stale managed seed files)."
        ),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview seed reconciliation changes without deleting managed artifacts.",
    ),
) -> None:
    """Skill operations."""
    if list_commands and ctx.invoked_subcommand is None:
        show_command_group("Skills", ["list", "describe", "run", "export"])
        raise click.exceptions.Exit(0)

    if dry_run and not regenerate_seeds:
        typer.echo("ERROR: --dry-run requires --regenerate-seeds", err=True)
        raise click.exceptions.Exit(2)

    if not full_bootstrap and not regenerate_seeds:
        if ctx.invoked_subcommand is None:
            show_command_group("Skills", ["list", "describe", "run", "export"])
            raise click.exceptions.Exit(0)
        return
    if ctx.invoked_subcommand is not None:
        return
    _run_full_bootstrap(regenerate_seeds=regenerate_seeds, dry_run=dry_run)


@app.command("list")
def list_cmd() -> None:
    """List Cmd."""
    emit_skills_list(list_skills(), output_json=_ctx_json(), emit_fn=_emit_skills_json)


@app.command("describe")
def describe(name: str) -> None:
    """Describe."""
    emit_skill_description(
        name, get_skill(name), output_json=_ctx_json(), emit_fn=_emit_skills_json
    )


@app.command("run")
def run(
    name: str,
    execute: bool = typer.Option(
        False,
        "--execute",
        help="Execute fallback CLI commands. Default is dry-run policy planning.",
    ),
) -> None:
    """Run a skill in dry-run or execute mode."""
    enforce_pipeline = (
        os.environ.get("SDD_ENFORCE_PIPELINE_CORRECT", "0").strip().lower()
        in _TRUE_VALUES
    )
    if enforce_pipeline and name == "sdd-correct":
        emit_pipeline_required(name, output_json=_ctx_json(), emit_fn=_emit_skills_json)
    engine = SkillEngine()
    result = engine.run_skill(name, execute=execute, profile=name)
    emit_skill_run_result(result, output_json=_ctx_json(), emit_fn=_emit_skills_json)


@app.command("export")
def export(
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Export format",
    ),
) -> None:
    """Export skill definitions in a machine-consumable format."""
    format = format.strip().lower()
    if format not in {"json", "openai", "langchain", "crewai", "autogen"}:
        raise typer.BadParameter(
            "format must be one of: json, openai, langchain, crewai, autogen."
        )
    emit_skills_export(
        format,
        export_skills_payload(format),
        output_json=_ctx_json(),
        emit_fn=_emit_skills_json,
    )
