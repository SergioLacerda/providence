"""providence_runtime telemetry, session, and dossier integration for ``providence ask``."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from providence_runtime import OtelBridge, RuntimeEvent, TelemetrySink
from providence_runtime.otel import OtlpHttpExporter

from providence_cli.services.ask_dossier import (
    build_dossier_lines as _build_dossier_lines,
)
from providence_cli.services.ask_dossier import (
    resolve_dossier_budget as _resolve_dossier_budget,
)
from providence_cli.services.ask_telemetry import (
    emit_ask_telemetry as _emit_ask_telemetry_impl,
)
from providence_cli.services.ask_telemetry import enqueue_flush as _enqueue_flush
from providence_cli.services.ask_telemetry import resolve_tokens as _resolve_tokens
from providence_cli.services.ask_telemetry import (
    upsert_ask_session as _upsert_ask_session_impl,
)
from providence_cli.services.ask_telemetry_worker import _EventSink
from providence_cli.services.ask_telemetry_worker import (
    build_ask_telemetry_sink as _build_ask_telemetry_sink_impl,
)

__all__ = [
    "OtelBridge",
    "OtlpHttpExporter",
    "TelemetrySink",
    "_build_ask_telemetry_sink",
    "_build_dossier_lines",
    "_enqueue_flush",
    "_resolve_dossier_budget",
    "_resolve_tokens",
]

logger = logging.getLogger(__name__)


def _emit_ask_telemetry(
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
    sink: _EventSink | None = None,
    flush: bool = True,
) -> RuntimeEvent | None:
    from providence_cli.commands import _ask_backend as _backend

    return _emit_ask_telemetry_impl(
        event_name,
        command=command,
        workspace_root=workspace_root,
        trace_id=trace_id,
        agent_id=agent_id,
        fingerprint=fingerprint,
        context_source=context_source,
        mandates_count=mandates_count,
        profile=profile,
        state=state,
        drift_detected=drift_detected,
        query_hash=query_hash,
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
        extra_details=extra_details,
        parent_event_id=parent_event_id,
        logger=logger,
        sink=sink,
        flush=flush,
        telemetry_sink_cls=_backend.TelemetrySink,
        otel_bridge_cls=_backend.OtelBridge,
        otlp_exporter_cls=_backend.OtlpHttpExporter,
    )


def _build_ask_telemetry_sink(workspace_root: Path) -> _EventSink:
    from providence_cli.commands import _ask_backend as _backend

    return _build_ask_telemetry_sink_impl(
        workspace_root,
        telemetry_sink_cls=_backend.TelemetrySink,
        otel_bridge_cls=_backend.OtelBridge,
        otlp_exporter_cls=_backend.OtlpHttpExporter,
    )


def _upsert_ask_session(
    workspace_root: Path,
    agent_id: str,
    work_item_id: str,
    artifact_fingerprint: str,
) -> None:
    _upsert_ask_session_impl(
        workspace_root=workspace_root,
        agent_id=agent_id,
        work_item_id=work_item_id,
        artifact_fingerprint=artifact_fingerprint,
        logger=logger,
    )


def _capture_effective_tokens(
    tokens_input: int | None, tokens_output: int | None
) -> tuple[int | None, int | None]:
    """Capture token counts from CLI flags or environment variables."""
    effective_tokens_input, effective_tokens_output, _ = (
        _capture_effective_tokens_with_source(tokens_input, tokens_output)
    )
    return effective_tokens_input, effective_tokens_output


def _capture_effective_tokens_with_source(
    tokens_input: int | None, tokens_output: int | None
) -> tuple[int | None, int | None, str]:
    """Capture token counts and source from CLI flags or environment variables."""
    from providence_runtime.llm import SimulatedTokenCapture

    effective_tokens_input = tokens_input
    effective_tokens_output = tokens_output
    token_source = (
        "cli" if tokens_input is not None or tokens_output is not None else ""
    )
    if effective_tokens_input is None or effective_tokens_output is None:
        captured = SimulatedTokenCapture().capture_from_env()
        if captured:
            if effective_tokens_input is None:
                effective_tokens_input = captured.tokens_input
            if effective_tokens_output is None:
                effective_tokens_output = captured.tokens_output
            token_source = token_source or "env"
    return effective_tokens_input, effective_tokens_output, token_source or "unknown"
