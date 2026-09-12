"""Telemetry/session helpers for ask command flows."""

from __future__ import annotations

import contextlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providence_runtime import (
    OtelBridge,
    RuntimeEvent,
    SessionManager,
    SessionState,
    TelemetrySink,
    get_otel_endpoint,
    is_sensitive_event,
)
from providence_runtime.otel import OtlpHttpExporter

from providence_cli.services._ask_telemetry_support import (
    build_sink,
    build_telemetry_details,
    resolve_status,
    resolve_workspace_id,
)
from providence_cli.services.ask_telemetry_worker import (
    _EventSink,
    enqueue_flush,
    route_canonical_event,
)
from providence_cli.utils.telemetry_paths import resolve_compliance_events_path

__all__ = [
    "emit_ask_telemetry",
    "enqueue_flush",
    "resolve_tokens",
    "route_canonical_event",
    "upsert_ask_session",
]


def resolve_tokens(query: str, output_text: str) -> tuple[int | None, int | None, str]:
    """Resolve token counts with explicit source.

    Source precedence:
    - env: `SDD_TOKENS_INPUT` / `SDD_TOKENS_OUTPUT` (canonical)
    - estimated: byte-based fallback (`len(text)//4`)
    """
    try:
        t_in = os.environ.get("SDD_TOKENS_INPUT", "").strip()
        t_out = os.environ.get("SDD_TOKENS_OUTPUT", "").strip()
        # Estimated counts floor at 1 for non-empty text: texts shorter than
        # 4 chars would estimate 0, which downstream telemetry cannot
        # distinguish from "no measurement" (null).
        tokens_in: int | None = (
            int(t_in)
            if t_in.isdigit()
            else (max(1, len(query) // 4) if query else None)
        )
        tokens_out: int | None = (
            int(t_out)
            if t_out.isdigit()
            else (max(1, len(output_text) // 4) if output_text else None)
        )
        source = "env" if t_in.isdigit() or t_out.isdigit() else "estimated"
        return tokens_in, tokens_out, source
    except Exception:
        return None, None, "unknown"


def _record_telemetry_degradation(
    workspace_root: Path, event_name: str, exc: Exception
) -> None:
    """Append a durable record that a *sensitive* event failed to emit.

    `emit_ask_telemetry` stays best-effort/non-blocking for every event
    `providence ask`'s primary function must never crash because telemetry is
    unavailable  but M007/M008 call for stronger obligations on sensitive
    events than silent, invisible best-effort (TEL-02,
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`). A
    `logger.debug` call is invisible in normal operation; this durable,
    append-only marker survives the process and is inspectable later, so
    the degradation is never silently lost even though emission itself is
    not retried or escalated. Itself best-effort: a failure here must never
    raise a *second* exception on top of the one already being handled.
    """
    with contextlib.suppress(Exception):
        marker_path = (
            workspace_root / ".providence" / "runtime" / "telemetry-degraded.jsonl"
        )
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": event_name,
            "reason": str(exc),
        }
        with marker_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")


def emit_ask_telemetry(
    event_name: str,
    *,
    command: str,
    workspace_root: Path,
    trace_id: str,
    agent_id: str,
    fingerprint: str,
    context_source: str,
    mandates_count: int,
    profile: str,
    state: str,
    drift_detected: bool,
    query_hash: str = "",
    path_id: str = "",
    start_ts: str = "",
    end_ts: str = "",
    duration_ms: int | None = None,
    context_bytes_loaded: int | None = None,
    tokens_input: int | None = None,
    tokens_output: int | None = None,
    retry_count: int | None = None,
    compression_ratio: float | None = None,
    phase_slow: bool = False,
    extra_details: dict[str, Any] | None = None,
    parent_event_id: str = "",
    logger: Any | None = None,
    sink: _EventSink | None = None,
    flush: bool = True,
    telemetry_sink_cls: type[TelemetrySink] = TelemetrySink,
    otel_bridge_cls: type[OtelBridge] = OtelBridge,
    otlp_exporter_cls: type[OtlpHttpExporter] = OtlpHttpExporter,
) -> RuntimeEvent | None:
    """Emit a typed RuntimeEvent to canonical JSONL sink. Best-effort.

    Returns the constructed `RuntimeEvent` (with its auto-generated
    `span_id`) so callers can link child events via `parent_event_id`.
    Returns `None` if emission failed (best-effort, never raises).

    Pass `sink` (from `build_ask_telemetry_sink`) to reuse one sink across
    several calls in the same `providence ask` invocation, and `flush=False` on all
    but the last call so the background flush happens once, not once per
    event (design.md D4). Defaults preserve prior behavior: build a fresh
    sink and flush immediately.
    """
    try:
        workspace_id = resolve_workspace_id(
            workspace_root=workspace_root, logger=logger
        )
        details = build_telemetry_details(
            context_source=context_source,
            mandates_count=mandates_count,
            drift_detected=drift_detected,
            profile=profile,
            state=state,
            query_hash=query_hash,
            extra_details=extra_details,
        )
        status = resolve_status(state)
        if sink is None:
            events_path = resolve_compliance_events_path(workspace_root=workspace_root)
            otel_endpoint = get_otel_endpoint()
            sink = build_sink(
                otel_endpoint=otel_endpoint,
                events_path=events_path,
                telemetry_sink_cls=telemetry_sink_cls,
                otel_bridge_cls=otel_bridge_cls,
                otlp_exporter_cls=otlp_exporter_cls,
            )
        event = RuntimeEvent(
            event=event_name,
            command=command,
            status=status,
            trace_id=trace_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
            artifact_fingerprint=fingerprint,
            decision_source_refs=["sdd-governance-context"],
            path_id=path_id,
            start_ts=start_ts,
            end_ts=end_ts,
            duration_ms=duration_ms,
            context_bytes_loaded=context_bytes_loaded,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            retry_count=retry_count,
            compression_ratio=compression_ratio,
            phase_slow=phase_slow,
            parent_event_id=parent_event_id,
            details=details,
        )
        sink.emit(event)
        if flush:
            enqueue_flush(sink)
        return event
    except Exception as exc:
        if logger is not None:
            logger.debug("Failed to emit ask telemetry: %s", exc)
        if is_sensitive_event(event_name):
            _record_telemetry_degradation(workspace_root, event_name, exc)
        return None


def upsert_ask_session(
    workspace_root: Path,
    agent_id: str,
    work_item_id: str,
    artifact_fingerprint: str,
    *,
    logger: Any | None = None,
) -> None:
    """Upsert SessionState for ask invocation. Best-effort."""
    try:
        workspace_id = resolve_workspace_id(
            workspace_root=workspace_root, logger=logger
        )
        schema_version = ""
        runtime_dir = workspace_root / ".providence" / "runtime"
        session = SessionState(
            workspace_id=workspace_id,
            agent_id=agent_id,
            work_item_id=work_item_id,
            artifact_fingerprint=artifact_fingerprint,
            schema_version=schema_version,
            policy_set_version=schema_version,
        )
        SessionManager(state_dir=runtime_dir).upsert(session)
    except Exception as exc:
        if logger is not None:
            logger.debug("Failed to upsert ask session: %s", exc)
