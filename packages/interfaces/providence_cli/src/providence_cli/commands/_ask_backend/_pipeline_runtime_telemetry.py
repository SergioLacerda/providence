"""providence ask  runtime telemetry emission and state persistence.

Split out of `_pipeline_runtime._sync_ask_runtime` (T1,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`):
these two functions are the side-effecting halves of that function's body
neither result is read after the call, so both extract cleanly with no
return value.
"""

from __future__ import annotations

from typing import Any

from providence_cli.services.ask_types import _AskInputs, _AskSessionContext

from ._pipeline_metrics import _maybe_record_llm_exchange_phase


def _emit_ask_runtime_telemetry(
    session: _AskSessionContext,
    *,
    context_source: str,
    fingerprint: str,
    mandates_count: int,
    drift_detected: bool,
    path_id: str,
    end_ts: str,
    duration_ms: int,
    tokens_in: int | None,
    tokens_out: int | None,
    token_source: str,
    degraded: bool,
    effective_degraded_reason: str,
    drift_type: str,
    trust_source: str,
    authenticated: bool,
    learning_signals: Any,
    inputs: _AskInputs,
    handbook_lookup: dict[str, Any] | None,
) -> None:
    """Emit the parent `governance.ask` event and its per-phase children.

    `ask.telemetry.emit` measures the cost of telemetry construction and
    emission itself (design.md 2/5  closes the F-09 phase-coverage gap).
    It is necessarily self-excluding: `session.phase_timer.records()` is
    read *inside* this phase's own `with` block, before this phase's own
    record is appended on exit, so this phase can never emit a
    `governance.ask.phase` event for itself in the same invocation. This
    is an inherent property of measuring the emitter from inside itself,
    not a bug  the duration is still visible in the console summary and
    `--full` dump (which read `phase_timer.records()` after this call
    returns).
    """
    from providence_cli.commands import _ask_backend as _backend
    from providence_cli.commands._ask_backend._helpers import _hash_query
    from providence_cli.commands._ask_backend._pipeline_runtime_support import (
        build_runtime_details,
    )

    with session.phase_timer.phase("ask.telemetry.emit", latency_domain="telemetry"):
        # One sink shared across every telemetry event this call emits
        # (parent + all phases), flushed once at the end instead of once per
        # event (design.md D4  was up to 6-7 separate flushes per `providence ask`
        # call).
        telemetry_sink = _backend._build_ask_telemetry_sink(session.workspace_root)
        parent_event = _backend._emit_ask_telemetry(
            "governance.ask",
            command="ask",
            workspace_root=session.workspace_root,
            trace_id=session.trace_id,
            agent_id=session.agent_id,
            fingerprint=fingerprint,
            context_source=context_source,
            mandates_count=mandates_count,
            profile=session.profile,
            state=session.state,
            drift_detected=drift_detected,
            query_hash=_hash_query(inputs.query),
            path_id=path_id,
            start_ts=session.start_ts,
            end_ts=end_ts,
            duration_ms=duration_ms,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            extra_details=build_runtime_details(
                fingerprint=fingerprint,
                degraded=degraded,
                degraded_reason=effective_degraded_reason,
                drift_type=drift_type,
                trust_source=trust_source,
                authenticated=authenticated,
                session=session,
                token_source=token_source,
                learning_signals=learning_signals,
                inputs=inputs,
                handbook_lookup=handbook_lookup
                if isinstance(handbook_lookup, dict)
                else None,
            ),
            sink=telemetry_sink,
            flush=False,
        )
        parent_span_id = getattr(parent_event, "span_id", "") or ""
        _maybe_record_llm_exchange_phase(session.phase_timer)
        for record in session.phase_timer.records():
            _backend._emit_ask_telemetry(
                "governance.ask.phase",
                command="ask",
                workspace_root=session.workspace_root,
                trace_id=session.trace_id,
                agent_id=session.agent_id,
                fingerprint=fingerprint,
                context_source=context_source,
                mandates_count=mandates_count,
                profile=session.profile,
                state=session.state,
                drift_detected=drift_detected,
                path_id=path_id,
                start_ts=record.start_ts,
                end_ts=record.end_ts,
                duration_ms=record.duration_ms,
                parent_event_id=parent_span_id,
                phase_slow=record.phase_slow,
                extra_details={
                    "phase_id": record.phase_id,
                    "latency_domain": record.latency_domain,
                    "measurement_quality": record.measurement_quality,
                    "observed_by": record.observed_by,
                    "failed": record.failed,
                    # Phase events inherit drift_detected from the parent
                    # invocation; without the classification they surface as
                    # missing_drift_type rows in audit drift tables.
                    "drift_type": drift_type,
                },
                sink=telemetry_sink,
                flush=False,
            )
        _backend._enqueue_flush(telemetry_sink)


def _persist_ask_runtime_state(
    session: _AskSessionContext,
    *,
    fingerprint: str,
    context_source: str,
    mandates_count: int,
    degraded: bool,
    effective_degraded_reason: str,
    trust_source: str,
    inputs: _AskInputs,
    ask_snapshot: dict[str, Any],
) -> None:
    """Persist the runtime cache/routing decision and upsert the session."""
    from providence_cli.commands import _ask_backend as _backend
    from providence_cli.commands._ask_backend._helpers import _now

    _backend._write_runtime_cache_and_routing_decision(
        session.workspace_root,
        {
            "ts": _now(),
            "trace_id": session.trace_id,
            "context_source": context_source,
            "compiled_fingerprint_used": fingerprint,
            "mandates_loaded": mandates_count,
            "agent_id": session.agent_id,
            "degraded": degraded,
            "degraded_reason": effective_degraded_reason,
            "trust_source": trust_source,
        },
        inputs.query,
        inputs.skill,
        fingerprint,
        {
            "organize_used": session.organize_used,
            "organize_reason": session.organize_reason,
            "handbook_task_type": ask_snapshot.get("handbook_task_type", ""),
        },
        ask_snapshot.get("_governance_snapshot_to_persist"),
    )
    _backend._upsert_ask_session(
        session.workspace_root, session.agent_id, "ask", fingerprint
    )
