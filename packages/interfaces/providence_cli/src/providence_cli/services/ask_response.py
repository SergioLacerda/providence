"""ask_response  final text response emission for `providence ask`.

Dossier helpers are injected as callables since they are thin wrappers
owned by `commands/_ask_backend.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import typer

from providence_cli.services.ask_response_intake import (
    _looks_like_implementation_intent,
    build_intake_contract_fields,
    resolve_execution_gate,
)
from providence_cli.services.ask_types import _AskInputs, _AskSessionContext


def _now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def emit_ask_text_response(
    inputs: _AskInputs,
    session: _AskSessionContext,
    ask_snapshot: dict[str, Any],
    output_text: str,
    governance_footer: str,
    *,
    duration_ms: int = 0,
    build_and_output_dossier_fn: Callable[..., None],
) -> None:
    """Echo the plain-text response and footer for `providence ask` to stdout."""
    mandates_count = ask_snapshot["mandates_count"]
    typer.echo(output_text)
    intake_mode = "multi" if session.organize_used else "none"
    gate = resolve_execution_gate(
        organize_used=session.organize_used,
        organize_reason=session.organize_reason,
    )
    gate_suffix = (
        ""
        if gate == "allowed"
        else "\ngate_reason       : intake_index_mode=none"
        f"\nintake_skipped    : {session.organize_reason} (query {len(inputs.query)} chars"
        " < 6000; pass 6000 chars or use: sdd-organize --input-file <path> <query>)"
    )
    typer.echo(
        f"intake_index_mode : {intake_mode}\n"
        f"intake_chunks     : {session.organize_chunks}\n"
        f"intake_retrieval  : {session.organize_retrieval}\n"
        f"intake_artifact   : {session.organize_artifact_path or 'n/a'}\n"
        f"governance_mode   : hard\n"
        f"execution_gate    : {gate}"
        f"{gate_suffix}"
    )
    intake_contract = build_intake_contract_fields(
        execution_gate=gate, query=inputs.query, skill=inputs.skill
    )
    typer.echo(
        f"intent            : {intake_contract['intent']}\n"
        f"entrypoint        : {intake_contract['entrypoint']}\n"
        f"next_action       : {intake_contract['next_action']}"
    )
    if _looks_like_implementation_intent(inputs.query):
        typer.echo(
            "providence ask contract  : governance-context query only\n"
            "delegation_status : not_executed\n"
            "next_valid_path   : implementation_handoff\n"
            "delegation_executed : false\n"
            "provider_bound    : false"
        )
    if inputs.dossier:
        build_and_output_dossier_fn(
            query=inputs.query,
            skill=inputs.skill,
            budget=inputs.budget,
            mandates_count=mandates_count,
            workspace_root=session.workspace_root,
        )
    typer.echo(governance_footer)
    phase_records = session.phase_timer.records()
    if inputs.full and phase_records:
        phase_timer = session.phase_timer
        typer.echo("timing:")
        typer.echo(
            f"  total_ms={duration_ms} "
            f"phase_total_ms={phase_timer.phase_total_ms()} "
            f"unattributed_ms="
            f"{phase_timer.unattributed_ms(session_duration_ms=duration_ms)}"
        )
        for record in phase_records:
            slow_marker = " SLOW" if record.phase_slow else ""
            typer.echo(
                f"  {record.phase_id}={record.duration_ms}ms "
                f"{record.latency_domain} {record.measurement_quality}{slow_marker}"
            )


def emit_ask_intake_only_text_response(
    inputs: _AskInputs,
    session: _AskSessionContext,
    *,
    runtime_handbook_hint: dict[str, Any] | None = None,
) -> None:
    """Cheap hook-mode text response: gate + structured intent only.

    Deliberately omits fingerprint, mandates count, degraded/drift status,
    full handbook payloads, and dossier/timing output  those require the full
    governance snapshot this profile exists to avoid loading (spike:
    20260714-sdd-ask-single-entrypoint-spike, A-005/I-005).
    """
    gate = resolve_execution_gate(
        organize_used=session.organize_used,
        organize_reason=session.organize_reason,
    )
    intake_contract = build_intake_contract_fields(
        execution_gate=gate, query=inputs.query, skill=inputs.skill
    )
    typer.echo(
        f"intake_index_mode : {'multi' if session.organize_used else 'none'}\n"
        f"intake_chunks     : {session.organize_chunks}\n"
        f"intake_retrieval  : {session.organize_retrieval}\n"
        f"intake_artifact   : {session.organize_artifact_path or 'n/a'}\n"
        f"governance_mode   : hard\n"
        f"execution_gate    : {gate}\n"
        f"intake_profile    : cheap\n"
        f"intent            : {intake_contract['intent']}\n"
        f"entrypoint        : {intake_contract['entrypoint']}\n"
        f"next_action       : {intake_contract['next_action']}\n"
        f"delegation_executed : false\n"
        f"provider_bound    : false"
    )
    if runtime_handbook_hint:
        runtime_doc = runtime_handbook_hint.get("runtime_doc")
        if runtime_doc:
            typer.echo(
                f"runtime_handbook : {runtime_handbook_hint.get('id', '')} -> "
                f"{runtime_doc}\n"
                f"runbook_reason   : "
                f"{runtime_handbook_hint.get('relevance_reason', '')}"
            )
        else:
            typer.echo(
                f"runtime_handbook : {runtime_handbook_hint.get('status', 'unknown')}"
                f" ({runtime_handbook_hint.get('diagnostic', '')})"
            )
