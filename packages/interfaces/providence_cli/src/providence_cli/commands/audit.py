"""providence audit  governance drift and telemetry summary."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from providence_cli.commands._audit_app import app
from providence_cli.commands._audit_command_support import emit_audit_view
from providence_cli.services.audit_formatters import (
    _ctx_json,
    _filter_events,
    _parse_since_date,
    render_audit_text,
    render_view_text,
)
from providence_cli.services.audit_runner import (
    _compute_base_summary,
    _default_events_path,
    _load_events,
    build_audit_summary_data,
)
from providence_cli.services.command_group_output import show_command_group
from providence_cli.shared.contracts import build_ok_result
from providence_cli.utils.output import emit_json

__all__ = ["app", "audit_export_commands"]


@app.callback()
def audit_run(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List audit commands."),
    events_file: Path = typer.Option(
        None, "--events-file", help="Path to compliance events JSONL."
    ),
    top: int = typer.Option(10, "--top", min=1, help="Number of drift rows to show."),
    include_non_drift: bool = typer.Option(
        False,
        "--include-non-drift",
        help="Include non-drift events in JSON output diagnostics.",
    ),
) -> None:
    """Summarize governance stats, top drifts, and token input/output comparison."""
    if ctx.invoked_subcommand is not None:
        return
    if list_commands:
        _show_audit_commands()
        raise typer.Exit(0)
    if events_file is None and top == 10 and not include_non_drift:
        _show_audit_commands()
        raise typer.Exit(0)
    _run_audit_summary(
        events_file=events_file,
        top=top,
        include_non_drift=include_non_drift,
    )


def _show_audit_commands() -> None:
    show_command_group(
        "Audit",
        [
            "summary",
            "view",
            "export",
            "legacy-check",
            "bootstrap-check",
            "compliance-pack",
        ],
    )


def _run_audit_summary(
    *,
    events_file: Path | None,
    top: int,
    include_non_drift: bool,
) -> None:
    source = events_file or _default_events_path()
    events = _load_events(source)
    now_utc = datetime.now(timezone.utc)
    data = build_audit_summary_data(events, top, now_utc, include_non_drift)
    data["events_file"] = str(source)

    if _ctx_json():
        emit_json(build_ok_result("audit", data))
        return

    computed = _compute_base_summary(events, top)
    render_audit_text(data, top, computed["rows"], source)


@app.command("summary")
def audit_summary(
    events_file: Path = typer.Option(
        None, "--events-file", help="Path to compliance events JSONL."
    ),
    top: int = typer.Option(10, "--top", min=1, help="Number of drift rows to show."),
    include_non_drift: bool = typer.Option(
        False,
        "--include-non-drift",
        help="Include non-drift events in JSON output diagnostics.",
    ),
) -> None:
    """Summarize governance stats, top drifts, and token input/output comparison."""
    _run_audit_summary(
        events_file=events_file,
        top=top,
        include_non_drift=include_non_drift,
    )


@app.command("view")
def audit_view(
    events_file: Path = typer.Option(
        None, "--events-file", help="Path to compliance events JSONL."
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Include events with timestamp >= since (ISO date/datetime).",
    ),
    event_type: str | None = typer.Option(
        None, "--event-type", help="Filter by event name (for example: VIOLATION)."
    ),
) -> None:
    """View compliance events with optional filtering."""
    source = events_file or _default_events_path()
    events = _load_events(source)
    since_dt = _parse_since_date(since)
    filtered = _filter_events(events, since=since_dt, event_type=event_type)
    emit_audit_view(
        source,
        filtered,
        since=since,
        event_type=event_type,
        output_json=_ctx_json(),
        render_view_text=render_view_text,
    )


# Imported for its @app.command() registration side effect  export/
# legacy-check/bootstrap-check/compliance-pack live in audit_export_commands.py
# (T12 split) but must be imported here so lazy command loading (which only
# imports `providence_cli.commands.audit`) still registers them on `app`. Mirrors the
# existing `_ask_backend/__init__.py` pattern for `_ask_cmd_impl`.
from providence_cli.commands import audit_export_commands  # noqa: E402,F401
