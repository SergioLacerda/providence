"""Analysis workspace commands  list, status, and clean analysis missions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import click
import typer

from providence_cli.services.analysis_helpers import (
    _STATES,
    _analysis_root,
    _collect_expired,
    _collect_missions,
    _next_action,
    _parse_duration,
)
from providence_cli.services.command_group_output import show_command_group
from providence_cli.utils.output import emit_json, is_json_mode
from providence_cli.utils.providence_authority import resolve_workspace_root


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


app = typer.Typer(help="Analysis workspace management", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def analysis_default(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List analysis commands."),
) -> None:
    """List missions when called without a subcommand."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Analysis", ["list", "status", "clean"])
        raise typer.Exit(0)


@app.command("list")
def list_missions(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """List analysis missions grouped by state."""
    ws_root = resolve_workspace_root()
    if ws_root is None:
        typer.echo("Error: workspace root not found.", err=True)
        raise typer.Exit(1)

    missions = _collect_missions(_analysis_root(ws_root))

    if _ctx_json() or json_output:
        emit_json({"command": "analysis list", "ok": True, "data": missions})
        return

    any_mission = any(missions[s] for s in _STATES)
    if not any_mission:
        typer.echo("No analysis missions found.")
        return
    for state in _STATES:
        items = missions[state]
        typer.echo(f"\n[{state.upper()}]")
        if not items:
            typer.echo("  (empty)")
            continue
        for item in items:
            typer.echo(f"  {item['mission_id']}  {item['date']}")


@app.command("status")
def mission_status(
    mission_id: str = typer.Argument(..., help="Mission id to inspect"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Show phase, artifacts, and blockers for a mission."""
    ws_root = resolve_workspace_root()
    if ws_root is None:
        typer.echo("Error: workspace root not found.", err=True)
        raise typer.Exit(1)

    root = _analysis_root(ws_root)
    found: dict[str, Any] | None = None

    for state in _STATES:
        candidate = root / state / f"{mission_id}.md"
        if candidate.exists():
            found = {
                "mission_id": mission_id,
                "state": state,
                "artifact": str(candidate),
                "next_action": _next_action(state),
            }
            break

    if found is None:
        msg = f"Mission '{mission_id}' not found. Run `sdd analysis list` to see available missions."
        if _ctx_json() or json_output:
            emit_json(
                {
                    "command": "analysis status",
                    "ok": False,
                    "data": {},
                    "error": {"code": "mission_not_found", "message": msg},
                }
            )
        else:
            typer.echo(f"Error: {msg}", err=True)
        raise typer.Exit(1)

    if _ctx_json() or json_output:
        emit_json({"command": "analysis status", "ok": True, "data": found})
        return

    typer.echo(f"mission_id : {found['mission_id']}")
    typer.echo(f"state      : {found['state']}")
    typer.echo(f"artifact   : {found['artifact']}")
    typer.echo(f"next_action: {found['next_action']}")


@app.command("clean")
def clean_missions(
    older_than: str = typer.Option(
        "30d",
        "--older-than",
        help="Remove missions older than this duration (e.g. 30d, 7d, 12h)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without deleting"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Remove completed missions from done/ older than the given duration."""
    ws_root = resolve_workspace_root()
    if ws_root is None:
        typer.echo("Error: workspace root not found.", err=True)
        raise typer.Exit(1)

    delta = _parse_duration(older_than)
    if delta is None:
        typer.echo(
            f"Error: invalid duration '{older_than}'. Use format: 30d, 12h, 60m",
            err=True,
        )
        raise typer.Exit(1)

    done_dir = _analysis_root(ws_root) / "done"
    cutoff = datetime.now(tz=timezone.utc) - delta
    removed = _collect_expired(done_dir, cutoff, dry_run)

    count = len(removed)
    suffix = " (dry-run)" if dry_run else ""

    if _ctx_json() or json_output:
        emit_json(
            {
                "command": "analysis clean",
                "ok": True,
                "data": {"removed": count, "dry_run": dry_run, "files": removed},
            }
        )
        return

    typer.echo(f"{count} mission(s) removed{suffix}.")
    if dry_run and removed:
        for f in removed:
            typer.echo(f"  would remove: {f}")
