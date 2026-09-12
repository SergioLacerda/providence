"""providence ask  runtime telemetry sync and command implementation."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from providence_cli.commands._ask_backend._pipeline_runtime_support import (
    emit_ask_response,
    normalize_ask_inputs,
    run_intake_only_ask,
)
from providence_cli.services.ask_response import (
    emit_ask_intake_only_text_response as _emit_ask_intake_only_text_response,
)
from providence_cli.services.ask_response import (
    emit_ask_text_response as _emit_ask_text_response,
)
from providence_cli.services.ask_response_intake import (
    emit_ask_intake_only_json_response as _emit_ask_intake_only_json_response,
)
from providence_cli.services.ask_response_json import (
    emit_ask_json_response as _emit_ask_json_response,
)
from providence_cli.services.ask_types import _AskInputs, _AskSessionContext

from ._helpers import (
    _normalize_typer_value,
    _now,
    _prefer_full_summary,
    _render_context_output,
    _resolve_ask_degraded_reason,
    _resolve_ask_drift_type,
)
from ._helpers_signals import _json_mode
from ._pipeline_metrics import _resolve_runtime_token_metrics, print_ask_console_summary
from ._pipeline_runtime_telemetry import (
    _emit_ask_runtime_telemetry,
    _persist_ask_runtime_state,
)
from ._pipeline_session import _load_ask_snapshot, _start_ask_session
from ._telemetry import _resolve_dossier_budget
from ._telemetry_dossier import _build_and_output_dossier, _handle_dossier_error

logger = logging.getLogger(__name__)


def _sync_ask_runtime(
    inputs: _AskInputs,
    session: _AskSessionContext,
    ask_snapshot: dict[str, Any],
) -> tuple[str, str, int]:
    from providence_cli.commands import _ask_backend as _backend

    context_source = ask_snapshot["context_source"]
    fingerprint = ask_snapshot["fingerprint"]
    mandates_count = ask_snapshot["mandates_count"]
    authenticated = ask_snapshot["authenticated"]
    degraded = ask_snapshot["degraded"]
    degrade_reason = ask_snapshot["degrade_reason"]
    trust_source = ask_snapshot["trust_source"]
    drift_detected = ask_snapshot["drift_detected"]
    root_seed_drift_detected = ask_snapshot["root_seed_drift_detected"]
    learning_signals = ask_snapshot["learning_signals"]
    handbook_lookup = ask_snapshot.get("handbook_lookup")
    end_ts = _now()
    duration_ms = int((time.monotonic() - session.start_mono) * 1000)
    output_text = _render_context_output(
        fingerprint,
        mandates_count,
        degraded=degraded,
        degrade_reason=degrade_reason,
    )
    tokens_in, tokens_out, token_source = _resolve_runtime_token_metrics(
        inputs, output_text
    )
    path_id = os.environ.get("SDD_PATH_ID") or (
        "PATH_B" if session.organize_used else "PATH_A"
    )
    drift_type = _resolve_ask_drift_type(
        drift_detected=drift_detected, authenticated=authenticated
    )
    effective_degraded_reason = _resolve_ask_degraded_reason(
        degraded=degraded, degrade_reason=degrade_reason, authenticated=authenticated
    )
    _emit_ask_runtime_telemetry(
        session,
        context_source=context_source,
        fingerprint=fingerprint,
        mandates_count=mandates_count,
        drift_detected=drift_detected,
        path_id=path_id,
        end_ts=end_ts,
        duration_ms=duration_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        token_source=token_source,
        degraded=degraded,
        effective_degraded_reason=effective_degraded_reason,
        drift_type=drift_type,
        trust_source=trust_source,
        authenticated=authenticated,
        learning_signals=learning_signals,
        inputs=inputs,
        handbook_lookup=handbook_lookup,
    )
    _persist_ask_runtime_state(
        session,
        fingerprint=fingerprint,
        context_source=context_source,
        mandates_count=mandates_count,
        degraded=degraded,
        effective_degraded_reason=effective_degraded_reason,
        trust_source=trust_source,
        inputs=inputs,
        ask_snapshot=ask_snapshot,
    )
    return (
        output_text,
        _backend._governance_footer_for_state(
            state=session.state,
            profile=session.profile,
            drift_detected=drift_detected,
            root_seed_drift_detected=root_seed_drift_detected,
        ),
        duration_ms,
    )


def _ask_cmd_impl(
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
    intake_only: bool = False,
) -> None:
    entry_mono = time.monotonic()
    inputs = normalize_ask_inputs(
        query=query,
        dossier=dossier,
        skill=skill,
        budget=budget,
        full=full,
        log_path=log_path,
        log_format=log_format,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        normalize_value_fn=_normalize_typer_value,
    )
    from providence_cli.commands import _ask_backend as _backend

    session = _start_ask_session(inputs.query, inputs.skill, entry_mono=entry_mono)
    if intake_only:
        run_intake_only_ask(
            inputs,
            session,
            build_runtime_handbook_hint_fn=_backend.build_runtime_handbook_hint,
            json_mode_fn=_json_mode,
            emit_intake_only_json_response_fn=_emit_ask_intake_only_json_response,
            emit_intake_only_text_response_fn=_emit_ask_intake_only_text_response,
        )
        return
    ask_snapshot = _load_ask_snapshot(inputs, session)
    output_text, governance_footer, duration_ms = _sync_ask_runtime(
        inputs, session, ask_snapshot
    )
    # Recorded after ask.telemetry.emit already ran and flushed this
    # invocation's governance.ask.phase events, so ask.response.render has
    # no JSONL row of its own for *this* call  same self-measurement
    # constraint as ask.telemetry.emit (see _sync_ask_runtime). It is still
    # visible in the console summary below and in --full's timing dump.
    with session.phase_timer.phase("ask.response.render", latency_domain="rendering"):
        emit_ask_response(
            inputs=inputs,
            session=session,
            ask_snapshot=ask_snapshot,
            output_text=output_text,
            governance_footer=governance_footer,
            duration_ms=duration_ms,
            json_mode_fn=_json_mode,
            emit_json_response_fn=_emit_ask_json_response,
            emit_text_response_fn=_emit_ask_text_response,
            resolve_dossier_budget_fn=_resolve_dossier_budget,
            load_dossier_artifact_fn=_backend._load_dossier_artifact,
            build_dossier_lines_fn=_backend._build_dossier_lines,
            handle_dossier_error_fn=_handle_dossier_error,
            prefer_full_summary_fn=_prefer_full_summary,
            build_and_output_dossier_fn=_build_and_output_dossier,
        )
    if not _json_mode():
        print_ask_console_summary(session.phase_timer, entry_mono=entry_mono)
