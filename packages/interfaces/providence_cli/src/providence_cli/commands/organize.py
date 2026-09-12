"""`providence organize` implementation helpers for indexed context preparation."""

from __future__ import annotations

from pathlib import Path

import click
import typer

from providence_cli.commands._ask_backend import _resolve_workspace_root
from providence_cli.services.ask_organize import run_sdd_organize, should_use_organize
from providence_cli.services.command_group_output import show_command_group
from providence_cli.shared.contracts import build_ok_result
from providence_cli.utils.output import emit_json, is_json_mode

app = typer.Typer(
    help="Prepare large context into indexed artifacts (sdd-organize).",
    context_settings={"allow_interspersed_args": True},
)


def organize_cmd(
    query: str = typer.Argument(..., help="Input text to organize and index."),
    input_file: Path | None = typer.Option(
        None, "--input-file", help="Optional file source for large logs/context."
    ),
    output_json: bool = typer.Option(
        False, "--output-json", help="Emit only structured JSON summary."
    ),
) -> None:
    """Run indexed context preparation and persist runtime artifact."""
    workspace_root = _resolve_workspace_root()
    source_text = (
        input_file.read_text(encoding="utf-8") if input_file is not None else query
    )
    _json_mode = output_json or is_json_mode(click.get_current_context(silent=True))
    if input_file is None and len(query) < 200 and not _json_mode:
        typer.echo(
            f"  sdd-organize: indexing query string only ({len(query)} chars). "
            "Pass --input-file <path> to index file content.",
            err=True,
        )
    should_heavy, reason = should_use_organize(source_text)
    if not should_heavy:
        reason = "forced_organize_light_input"
    artifact, out_path = run_sdd_organize(
        workspace_root=workspace_root,
        query=query,
        source_text=source_text,
        route_reason=reason,
    )
    data = {
        "intake_index_mode": "multi",
        "intake_chunks": len(artifact.get("chunks", [])),
        "intake_retrieval": artifact.get("retrieval_policy", "indexed_only"),
        "artifact_path": str(out_path),
        "exit_code": 0,
    }
    if _json_mode:
        payload = build_ok_result("organize", data)
        emit_json(payload)
        return
    summary = data
    typer.echo("sdd-organize completed")
    typer.echo(f"artifact_path    : {out_path}")
    typer.echo(f"intake_chunks    : {summary['intake_chunks']}")
    typer.echo(f"intake_retrieval : {summary['intake_retrieval']}")


@app.callback(invoke_without_command=True)
def organize(
    query: str | None = typer.Argument(None, help="Input text to organize and index."),
    list_commands: bool = typer.Option(False, "--list", help="List organize commands."),
    input_file: Path | None = typer.Option(
        None, "--input-file", help="Optional file source for large logs/context."
    ),
    output_json: bool = typer.Option(
        False, "--output-json", help="Emit only structured JSON summary."
    ),
) -> None:
    """Run indexed context preparation and persist runtime artifact."""
    if list_commands:
        show_command_group("Organize", ["<query> [--input-file PATH]"])
        raise typer.Exit(0)
    if query is None:
        raise click.UsageError("Missing argument 'QUERY'.")
    organize_cmd(query=query, input_file=input_file, output_json=output_json)
