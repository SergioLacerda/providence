"""Support helpers for `providence ask` pipeline runtime orchestration."""

from __future__ import annotations

from typing import Any

from providence_cli.services.ask_types import _AskInputs, _AskSessionContext


def run_intake_only_ask(
    inputs: _AskInputs,
    session: _AskSessionContext,
    *,
    build_runtime_handbook_hint_fn: Any,
    json_mode_fn: Any,
    emit_intake_only_json_response_fn: Any,
    emit_intake_only_text_response_fn: Any,
) -> None:
    """Cheap hook-mode profile (spike: 20260714-sdd-ask-single-entrypoint-spike,
    I-005). Deliberately skips build_governed_ask_snapshot (compiled-governance
    load, signature verification, drift checks, full handbook payload) and
    telemetry/runtime-cache writes  those are the stages the spike identified
    as unnecessary for every hook-fired prompt. A compact runtime handbook hint
    is still allowed because it reads only `.providence/source/handbook/**` and stays
    opportunistic.
    """
    handbook_hint = build_runtime_handbook_hint_fn(
        root=session.workspace_root,
        query=inputs.query,
        skill=inputs.skill,
        cached_handbook_task_type=session.cached_handbook_task_type,
    )
    if json_mode_fn():
        emit_intake_only_json_response_fn(
            inputs, session, runtime_handbook_hint=handbook_hint
        )
    else:
        emit_intake_only_text_response_fn(
            inputs, session, runtime_handbook_hint=handbook_hint
        )


def normalize_ask_inputs(
    *,
    query: str,
    dossier: bool,
    skill: str | None,
    budget: int | None,
    full: bool,
    log_path: str | None,
    log_format: str,
    tokens_input: int | None,
    tokens_output: int | None,
    normalize_value_fn: Any,
) -> _AskInputs:
    skill_value = normalize_value_fn(skill, None)
    budget_value = normalize_value_fn(budget, None)
    log_path_value = normalize_value_fn(log_path, None)
    log_format_value = normalize_value_fn(log_format, "jsonl")
    tokens_input_value = normalize_value_fn(tokens_input, None)
    tokens_output_value = normalize_value_fn(tokens_output, None)
    return _AskInputs(
        query=query,
        dossier=bool(normalize_value_fn(dossier, False)),
        skill=skill_value if isinstance(skill_value, str) else None,
        budget=budget_value if isinstance(budget_value, int) else None,
        full=bool(normalize_value_fn(full, False)),
        log_path=log_path_value if isinstance(log_path_value, str) else None,
        log_format=log_format_value if isinstance(log_format_value, str) else "jsonl",
        tokens_input=tokens_input_value
        if isinstance(tokens_input_value, int)
        else None,
        tokens_output=tokens_output_value
        if isinstance(tokens_output_value, int)
        else None,
    )


def build_runtime_details(
    *,
    fingerprint: str,
    degraded: bool,
    degraded_reason: str,
    drift_type: str,
    trust_source: str,
    authenticated: bool,
    session: _AskSessionContext,
    token_source: str,
    learning_signals: dict[str, int],
    inputs: _AskInputs,
    handbook_lookup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details = {
        "compiled_fingerprint_used": fingerprint,
        "degraded": degraded,
        "degraded_reason": degraded_reason,
        "drift_type": drift_type,
        "trust_source": trust_source,
        "authenticated": authenticated,
        "intake_route": "heavy" if session.organize_used else "light",
        "intake_route_reason": session.organize_reason,
        "intake_artifact": session.organize_artifact_path,
        "intake_chunks": session.organize_chunks,
        "intake_retrieval": session.organize_retrieval,
        "token_source": token_source,
        "learning_signal_count": sum(
            value
            for key, value in learning_signals.items()
            if key not in {"observed_events", "window_days"}
        ),
        "full_mode": inputs.full,
        "log_format": inputs.log_format,
        "log_path": inputs.log_path or "default",
    }
    if handbook_lookup is not None:
        matches = handbook_lookup.get("matches", [])
        details["handbook_lookup_status"] = handbook_lookup.get("status", "unknown")
        details["handbook_lookup_diagnostic"] = handbook_lookup.get("diagnostic", "")
        details["handbook_match_count"] = (
            len(matches) if isinstance(matches, list) else 0
        )
    return details


def emit_ask_response(
    *,
    inputs: _AskInputs,
    session: _AskSessionContext,
    ask_snapshot: dict[str, Any],
    output_text: str,
    governance_footer: str,
    duration_ms: int,
    json_mode_fn: Any,
    emit_json_response_fn: Any,
    emit_text_response_fn: Any,
    resolve_dossier_budget_fn: Any,
    load_dossier_artifact_fn: Any,
    build_dossier_lines_fn: Any,
    handle_dossier_error_fn: Any,
    prefer_full_summary_fn: Any,
    build_and_output_dossier_fn: Any,
) -> None:
    if json_mode_fn():
        emit_json_response_fn(
            inputs,
            session,
            ask_snapshot,
            governance_footer,
            duration_ms=duration_ms,
            resolve_dossier_budget_fn=resolve_dossier_budget_fn,
            load_dossier_artifact_fn=load_dossier_artifact_fn,
            build_dossier_lines_fn=build_dossier_lines_fn,
            handle_dossier_error_fn=handle_dossier_error_fn,
            prefer_full_summary_fn=prefer_full_summary_fn,
        )
        return
    emit_text_response_fn(
        inputs,
        session,
        ask_snapshot,
        output_text,
        governance_footer,
        duration_ms=duration_ms,
        build_and_output_dossier_fn=build_and_output_dossier_fn,
    )
