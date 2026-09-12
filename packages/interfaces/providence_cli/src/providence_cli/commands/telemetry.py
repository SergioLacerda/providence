"""providence telemetry  inspect and manage local compliance-events telemetry."""

from __future__ import annotations

import typer

from providence_cli.commands._telemetry_app import _ctx_json, _resolve_events_path, app
from providence_cli.commands._telemetry_command_support import (
    abort_invalid_format,
    emit_dump,
    emit_status,
)
from providence_cli.services.command_group_output import show_command_group
from providence_cli.services.telemetry_handler import (
    _event_ts,  # noqa: F401  backward-compat re-export for unit tests
    _parse_ts,  # noqa: F401  backward-compat re-export for unit tests
    _read_events,
    build_status_data,
    filter_events,
)

__all__ = ["_event_ts", "_parse_ts", "app", "telemetry_query"]


@app.callback()
def telemetry_default(
    ctx: typer.Context,
    list_commands: bool = typer.Option(
        False, "--list", help="List telemetry commands."
    ),
) -> None:
    """Show telemetry status summary (default when no subcommand given)."""
    if ctx.invoked_subcommand is not None:
        return
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Telemetry", ["status", "dump", "query", "summary", "init"])
        raise typer.Exit(0)


def _print_status() -> None:
    path = _resolve_events_path("telemetry status")
    emit_status(path, build_status_data(path), output_json=_ctx_json())


@app.command()
def status() -> None:
    """Show telemetry file status and event-type breakdown."""
    _print_status()


@app.command()
def dump(
    limit: int = typer.Option(
        50, "--limit", "-n", help="Max events to print (newest first)."
    ),
    event_type: str | None = typer.Option(
        None, "--event-type", "-t", help="Filter by event_type (case-insensitive)."
    ),
    trace_id: str | None = typer.Option(None, "--trace-id", help="Filter by trace_id."),
    fmt: str = typer.Option(
        "jsonl", "--format", "-f", help="Output format: jsonl (default) or json array."
    ),
) -> None:
    """Dump raw telemetry events as JSON lines."""
    path = _resolve_events_path("telemetry dump")
    if fmt not in {"json", "jsonl"}:
        abort_invalid_format(fmt, output_json=_ctx_json())
    events = _read_events(path)
    events = filter_events(events, event_type=event_type, trace_id=trace_id)
    emit_dump(
        path,
        events[-limit:],
        event_type=event_type,
        trace_id=trace_id,
        limit=limit,
        fmt=fmt,
        output_json=_ctx_json(),
    )


# Imported for its @app.command() registration side effect  query/summary/
# init live in telemetry_query.py (T13 split) but must be imported here so
# lazy command loading (which only imports `providence_cli.commands.telemetry`)
# still registers them on `app`. Mirrors the existing `_ask_backend/__init__.py`
# pattern for `_ask_cmd_impl`.
from providence_cli.commands import telemetry_query  # noqa: E402,F401
