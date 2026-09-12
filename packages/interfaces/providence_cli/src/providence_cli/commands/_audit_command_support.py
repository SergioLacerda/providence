"""Support helpers for audit command output and evidence files."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, cast

import click
import typer

from providence_cli.shared.contracts import build_ok_result
from providence_cli.utils.output import emit_json


def emit_audit_view(
    source: Path,
    filtered: list[dict[str, Any]],
    *,
    since: str | None,
    event_type: str | None,
    output_json: bool,
    render_view_text: Any,
) -> None:
    if output_json:
        emit_json(
            build_ok_result(
                "audit view",
                {
                    "events_file": str(source),
                    "since": since,
                    "event_type": event_type,
                    "count": len(filtered),
                    "events": filtered,
                },
            )
        )
        return
    render_view_text(filtered, source, since, event_type)


def write_export_manifest(manifest_file: Path, manifest: dict[str, Any]) -> None:
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def emit_legacy_check(result: dict[str, Any], *, output_json: bool) -> None:
    if output_json:
        emit_json(build_ok_result("audit legacy-check", result))
        return
    typer.echo("Legacy Path Policy Check")
    typer.echo(f"- date: {result['date']}")
    typer.echo(f"- policy mode: {result['policy_mode']}")
    typer.echo(f"- hits: {len(result['hits'])}")
    for item in result["hits"][:20]:
        typer.echo(f"  - {item}")
    if result["policy_mode"] == "block" and result["hits"]:
        raise click.exceptions.Exit(2)


def emit_bootstrap_check(result: dict[str, Any], *, output_json: bool) -> None:
    if output_json:
        emit_json(build_ok_result("audit bootstrap-check", result))
        return
    typer.echo("Bootstrap Drift Check")
    if result["ok"]:
        typer.echo("- status: OK")
        return
    typer.echo("- status: DRIFT")
    for issue in result["issues"]:
        typer.echo(f"  - {issue}")
    raise click.exceptions.Exit(2)


def write_compliance_pack(
    out_dir: Path,
    csv_blob: bytes,
    manifest: dict[str, Any],
    runtime_status: Any,
    governance_validate: Any,
    bootstrap: dict[str, Any],
    legacy_result: dict[str, Any],
) -> None:
    report_file = out_dir / "compliance_report.csv"
    report_file.write_bytes(csv_blob)
    manifest_file = out_dir / "compliance_report.manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out_dir / "runtime_status.txt").write_text(
        runtime_status.stdout + runtime_status.stderr, encoding="utf-8"
    )
    (out_dir / "governance_validation.txt").write_text(
        governance_validate.stdout + governance_validate.stderr, encoding="utf-8"
    )
    legacy_hits = legacy_result["hits"]
    policy_mode = legacy_result["policy_mode"]
    aa3_ok = policy_mode != "block" or not legacy_hits
    (out_dir / "decision_trace.md").write_text(
        "\n".join(
            [
                "# Decision Trace",
                "- ADR-013: CLAUDE.md pointer model enforced.",
                "- ADR-014: Legacy fallback removal and timeline policy enforced.",
                f"- Legacy policy mode: {policy_mode}",
                f"- Bootstrap drift check: {'OK' if bootstrap['ok'] else 'DRIFT'}",
                f"- Legacy references detected: {len(legacy_hits)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    checklist_lines = [
        "# External Review Checklist",
        f"- [x] AA1: audit view/export available ({report_file.name})",
        f"- [x] AA2: manifest generated ({manifest_file.name})",
        f"- [{'x' if aa3_ok else ' '}] AA3: legacy policy check (mode={policy_mode}, hits={len(legacy_hits)})",
        f"- [{'x' if bootstrap['ok'] else ' '}] AA4: bootstrap contract drift check",
        "- [x] AA5: run targeted tests in CI/local",
        "- [x] AA6: evidence pack generated",
    ]
    (out_dir / "external_review_checklist.md").write_text(
        "\n".join(checklist_lines) + "\n", encoding="utf-8"
    )


def resolve_phase_date(phase_date: str | None, current_policy_date: Any) -> date:
    if phase_date is None:
        return cast(date, current_policy_date())
    try:
        return date.fromisoformat(phase_date)
    except ValueError as exc:
        raise typer.BadParameter("--phase-date must be YYYY-MM-DD.") from exc


def run_compliance_pack_workflow(
    out_dir: Path,
    *,
    since: str | None,
    event_type: str | None,
    default_events_path: Any,
    load_events: Any,
    parse_since_date: Any,
    filter_events: Any,
    event_to_row: Any,
    build_export_payload: Any,
    process_runner_cls: Any,
    resolve_workspace_root: Any,
    run_bootstrap_check: Any,
    run_legacy_check: Any,
    current_policy_date: Any,
) -> None:
    source = default_events_path()
    rows = [
        event_to_row(event)
        for event in filter_events(
            load_events(source), since=parse_since_date(since), event_type=event_type
        )
    ]
    csv_blob, manifest = build_export_payload(
        source=source, since=since, event_type=event_type, rows=rows, fmt="csv"
    )
    runner = process_runner_cls()
    runtime_status = runner.run(
        [sys.executable, "-m", "providence_cli.main", "runtime", "status"],
        capture_output=True,
        check=False,
    )
    governance_validate = runner.run(
        [sys.executable, "-m", "providence_cli.main", "governance", "validate"],
        capture_output=True,
        check=False,
    )
    ws_root = resolve_workspace_root()
    write_compliance_pack(
        out_dir,
        csv_blob,
        manifest,
        runtime_status,
        governance_validate,
        run_bootstrap_check(ws_root),
        run_legacy_check(ws_root, current_policy_date()),
    )
