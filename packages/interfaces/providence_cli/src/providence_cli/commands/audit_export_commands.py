"""providence audit  export, legacy-check, bootstrap-check, compliance-pack subcommands.

Split out of `audit.py` (T12,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

from pathlib import Path

import click
import typer

from providence_cli.commands._audit_app import app
from providence_cli.commands._audit_command_support import (
    emit_bootstrap_check,
    emit_legacy_check,
    resolve_phase_date,
    run_compliance_pack_workflow,
    write_export_manifest,
)
from providence_cli.services.audit_export import _build_export_payload, _event_to_row
from providence_cli.services.audit_formatters import (
    _ctx_json,
    _filter_events,
    _parse_since_date,
)
from providence_cli.services.audit_runner import _default_events_path, _load_events
from providence_cli.services.audit_validators import (
    current_policy_date,
    run_bootstrap_check,
    run_legacy_check,
)
from providence_cli.utils.providence_authority import resolve_workspace_root
from providence_core.utils.process import SafeProcessRunner


@app.command("export")
def audit_export(
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
    format: str = typer.Option("csv", "--format", help="Export format."),  # noqa: A002
    manifest_file: Path = typer.Option(
        Path(".providence/runtime/compliance-export.manifest.json"),
        "--manifest-file",
        help="Where to write export manifest metadata.",
    ),
) -> None:
    """Export compliance events and write evidence manifest."""
    if (fmt := format.strip().lower()) != "csv":
        typer.echo("Only --format=csv is currently supported.")
        raise click.exceptions.Exit(2)
    source = events_file or _default_events_path()
    events = _load_events(source)
    since_dt = _parse_since_date(since)
    filtered = _filter_events(events, since=since_dt, event_type=event_type)
    rows = [_event_to_row(event) for event in filtered]
    csv_blob, manifest = _build_export_payload(
        source=source, since=since, event_type=event_type, rows=rows, fmt=fmt
    )
    # CSV data is emitted to stdout to support shell redirection.
    typer.echo(csv_blob.decode("utf-8"), nl=False)
    write_export_manifest(manifest_file, manifest)


@app.command("legacy-check")
def audit_legacy_check(
    phase_date: str | None = typer.Option(
        None, "--phase-date", help="Override policy date (YYYY-MM-DD) for testing."
    ),
) -> None:
    """Check `/legacy/**` usage against Q3/Q4 2026 enforcement policy."""
    root = resolve_workspace_root()
    emit_legacy_check(
        run_legacy_check(root, resolve_phase_date(phase_date, current_policy_date)),
        output_json=_ctx_json(),
    )


@app.command("bootstrap-check")
def audit_bootstrap_check() -> None:
    """Validate AGENTS/CLAUDE bootstrap contract drift."""
    root = resolve_workspace_root()
    emit_bootstrap_check(run_bootstrap_check(root), output_json=_ctx_json())


@app.command("compliance-pack")
def audit_compliance_pack(
    out_dir: Path = typer.Option(
        Path(".providence/runtime/compliance-pack"),
        "--out-dir",
        help="Directory for external-review compliance artifacts.",
    ),
    since: str | None = typer.Option(
        None, "--since", help="Filter exported events since ISO date/datetime."
    ),
    event_type: str | None = typer.Option(
        None, "--event-type", help="Filter exported events by event type."
    ),
) -> None:
    """Generate external-review compliance evidence bundle."""
    out_dir.mkdir(parents=True, exist_ok=True)
    from providence_cli.utils.dev_deps import require_dev_module

    require_dev_module("providence_cli")
    run_compliance_pack_workflow(
        out_dir,
        since=since,
        event_type=event_type,
        default_events_path=_default_events_path,
        load_events=_load_events,
        parse_since_date=_parse_since_date,
        filter_events=_filter_events,
        event_to_row=_event_to_row,
        build_export_payload=_build_export_payload,
        process_runner_cls=SafeProcessRunner,
        resolve_workspace_root=resolve_workspace_root,
        run_bootstrap_check=run_bootstrap_check,
        run_legacy_check=run_legacy_check,
        current_policy_date=current_policy_date,
    )
    typer.echo(f"Compliance pack written to: {out_dir}")
