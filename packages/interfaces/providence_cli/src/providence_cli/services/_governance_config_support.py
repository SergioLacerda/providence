"""Support helpers for governance load/validate handlers."""

from __future__ import annotations

from typing import Any

import typer
from rich.console import Console
from rich.table import Table


def render_summary_table(*, console: Console, summary: dict[str, Any]) -> None:
    table = Table(title="Governance Summary", show_header=True, header_style="bold")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    for key, value in summary.items():
        table.add_row(key, str(value))
    console.print(table)


def collect_validation_state(
    *,
    path: str,
    skip_handshake: bool,
    validate_path_fn: Any,
    load_config_fn: Any,
    check_files_accessible_fn: Any,
    check_fingerprints_valid_fn: Any,
    check_no_conflicts_fn: Any,
    check_artifact_consistency_fn: Any,
    run_runtime_preflight_fn: Any,
    check_root_seed_drift_fn: Any = None,
) -> dict[str, Any]:
    structure_ok = validate_path_fn(path)
    config = load_config_fn(path) if structure_ok else None
    consistency_ok, consistency_reason = check_artifact_consistency_fn(path)

    handshake_active = True
    if not skip_handshake:
        from providence_core.governance.handshake import AgentHandshakeProtocol

        handshake_active = AgentHandshakeProtocol().is_handshake_valid()

    preflight = run_runtime_preflight_fn(path)

    root_seed_drift_ok = True
    root_seed_drift_reason = "root-seed drift check not configured"
    if check_root_seed_drift_fn is not None:
        root_seed_drift_ok, root_seed_drift_reason = check_root_seed_drift_fn(path)

    checks = [
        ("Structure validation", structure_ok),
        ("Files accessible", check_files_accessible_fn(path)),
        ("Fingerprints valid", check_fingerprints_valid_fn(config)),
        ("No conflicts", check_no_conflicts_fn(config)),
        ("Artifact consistency", consistency_ok),
        ("Active handshake (M015)", handshake_active),
        ("Runtime preflight", preflight.passed),
        ("Root-seed drift", root_seed_drift_ok),
    ]
    check_payload = [{"check": name, "passed": bool(passed)} for name, passed in checks]
    return {
        "config": config,
        "consistency_ok": consistency_ok,
        "consistency_reason": consistency_reason,
        "handshake_active": handshake_active,
        "preflight": preflight,
        "preflight_ok": preflight.passed,
        "root_seed_drift_ok": root_seed_drift_ok,
        "root_seed_drift_reason": root_seed_drift_reason,
        "check_payload": check_payload,
        "all_passed": all(item["passed"] for item in check_payload),
    }


def render_validation_table(
    *, console: Console, check_payload: list[dict[str, Any]]
) -> None:
    table = Table(title="Validation Results", show_header=True, header_style="bold")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    for item in check_payload:
        status = "[green]PASS[/green]" if item["passed"] else "[red]FAIL[/red]"
        table.add_row(str(item["check"]), status)
    console.print(table)


def render_advisory_table(
    *,
    console: Console,
    advisory_payload: list[dict[str, Any]],
    render_status_fn: Any,
) -> None:
    advisory_table = Table(
        title="Language Governance Advisories",
        show_header=True,
        header_style="bold",
    )
    advisory_table.add_column("Check", style="cyan")
    advisory_table.add_column("Severity", style="yellow")
    advisory_table.add_column("Status", style="green")
    advisory_table.add_column("Message", style="white")
    for item in advisory_payload:
        advisory_table.add_row(
            str(item["check"]),
            str(item["severity"]).upper(),
            render_status_fn(str(item["status"])),
            str(item["message"]),
        )
    console.print(advisory_table)


def emit_validation_outcome(
    *,
    console: Console,
    all_passed: bool,
    handshake_active: bool,
    structure_ok: bool,
    consistency_ok: bool,
    consistency_reason: str,
    preflight_ok: bool,
    preflight_reason: str,
    root_seed_drift_ok: bool = True,
    root_seed_drift_reason: str = "root-seed drift check not configured",
) -> None:
    if not preflight_ok and preflight_reason:
        console.print(f"[yellow]runtime preflight: {preflight_reason}[/yellow]")
    if not consistency_ok:
        console.print(f"[yellow]artifact consistency: {consistency_reason}[/yellow]")
    if not root_seed_drift_ok:
        console.print(f"[yellow]root-seed drift: {root_seed_drift_reason}[/yellow]")
    if all_passed:
        console.print("[green]All validation checks passed[/green]")
        return
    console.print("[red]ERROR: Some validation checks failed[/red]")
    if not handshake_active:
        console.print(
            "  Next: run 'providence governance handshake --init' to formalize session"
        )
    if not structure_ok or not consistency_ok or not preflight_ok:
        console.print(
            "  Next: run 'providence governance compile' to rebuild artifacts"
        )
    if not root_seed_drift_ok:
        console.print(
            "  Next: run 'providence governance generate' to resync root seed files"
        )
    raise typer.Exit(1)


def normalize_signature_mode(signature_mode: str) -> str:
    normalized = signature_mode.strip().lower()
    if normalized not in {"off", "warn", "strict"}:
        raise typer.BadParameter("signature_mode must be off, warn, or strict.")
    return normalized
