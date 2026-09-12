"""providence telemetry  query, summary, init subcommands.

Split out of `telemetry.py` (T13,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

import typer

from providence_cli.commands._telemetry_app import _ctx_json, _resolve_events_path, app
from providence_cli.commands._telemetry_command_query import emit_init, emit_summary
from providence_cli.commands._telemetry_command_support import (
    abort_invalid_time_filter,
    emit_query,
)
from providence_cli.services.telemetry_handler import (
    _read_events,
    apply_time_filter,
    build_init_result,
    filter_events,
)


@app.command()
def query(
    event_type: str | None = typer.Option(
        None, "--event-type", "-t", help="Filter by event_type (case-insensitive)."
    ),
    status_filter: str | None = typer.Option(
        None, "--status", "-s", help="Filter by status field (e.g. ok, warn, fail)."
    ),
    level: str | None = typer.Option(
        None, "--level", "-l", help="Filter by level field (e.g. INFO, ERROR)."
    ),
    trace_id: str | None = typer.Option(None, "--trace-id", help="Filter by trace_id."),
    since: str | None = typer.Option(
        None,
        "--since",
        "--from",
        help="ISO datetime lower bound, e.g. 2026-05-01 or 2026-05-01T00:00:00Z.",
    ),
    until: str | None = typer.Option(
        None,
        "--until",
        "--to",
        help="ISO datetime upper bound.",
    ),
    work_item: str | None = typer.Option(
        None, "--work-item", "-w", help="Filter by work_item_id."
    ),
    limit: int = typer.Option(100, "--limit", "-n", help="Max events to return."),
) -> None:
    """Query telemetry events with optional filters (all filters are AND)."""
    path = _resolve_events_path("telemetry query")
    events = _read_events(path)
    events = filter_events(
        events,
        event_type=event_type,
        status_filter=status_filter,
        level=level,
        trace_id=trace_id,
        work_item=work_item,
    )

    events, since_error, until_error = apply_time_filter(events, since, until)

    if since_error is not None:
        abort_invalid_time_filter("since", since_error, output_json=_ctx_json())
    if until_error is not None:
        abort_invalid_time_filter("until", until_error, output_json=_ctx_json())
    emit_query(
        path,
        events[-limit:],
        len(events),
        event_type=event_type,
        status_filter=status_filter,
        level=level,
        trace_id=trace_id,
        since=since,
        until=until,
        work_item=work_item,
        limit=limit,
        output_json=_ctx_json(),
    )


@app.command()
def summary(
    phase_id: str | None = typer.Option(
        None, "--phase-id", help="Filter by details.phase_id."
    ),
    latency_domain: str | None = typer.Option(
        None, "--latency-domain", help="Filter by details.latency_domain."
    ),
    path_id: str | None = typer.Option(None, "--path-id", help="Filter by path_id."),
) -> None:
    """Aggregate governance.ask.phase events into per-phase latency statistics."""
    path = _resolve_events_path("telemetry summary")
    events = _read_events(path)
    events = filter_events(
        events,
        event_type="governance.ask.phase",
        phase_id=phase_id,
        latency_domain=latency_domain,
        path_id=path_id,
    )
    emit_summary(
        path,
        events,
        phase_id=phase_id,
        latency_domain=latency_domain,
        path_id=path_id,
        output_json=_ctx_json(),
    )


@app.command()
def init() -> None:
    """Initialize telemetry storage (.providence/runtime/ dir + empty JSONL file)."""
    path = _resolve_events_path("telemetry init")
    emit_init(path, build_init_result(path), output_json=_ctx_json())
