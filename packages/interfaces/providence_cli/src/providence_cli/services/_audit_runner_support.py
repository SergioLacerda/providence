"""Support helpers for audit analytics aggregation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from providence_cli.services._audit_window_support import (
    window_classification,
    window_confidence,
    window_correlation,
)
from providence_cli.services.audit_event_parser import (
    DriftRow,
    _is_ask_event,
    _is_ask_invocation,
    _is_ask_phase_event,
    _is_drift_event,
    _token_totals,
)
from providence_core.governance.compliance_constants import (
    resolve_compliance_log_override,
)

__all__ = [
    "compute_base_summary",
    "default_events_path",
    "window_classification",
    "window_confidence",
    "window_correlation",
]


def compute_base_summary(
    *,
    events: list[dict[str, Any]],
    top: int,
    drift_cause_fn: Any,
    drift_type_fn: Any,
    event_ts_fn: Any,
    ts_sort_key_fn: Any,
) -> dict[str, Any]:
    # governance.ask.phase sub-events inherit drift_detected from their parent
    # governance.ask invocation (~6 phases per invocation); counting them as
    # separate drifts inflates the numerator ~7x. Excluded here; drift-rate
    # denominators keep counting them (see ask_events below), matching the
    # windowed correlation shape in window_correlation().
    drifts = [
        event
        for event in events
        if _is_drift_event(event) and not _is_ask_phase_event(event)
    ]
    ask_events = [event for event in events if _is_ask_event(event)]
    events_by_command: dict[str, int] = {}
    drift_by_type: dict[str, int] = {}
    unclassified_drifts = 0
    for event in events:
        command = str(event.get("command", "")).strip() or "unknown"
        events_by_command[command] = events_by_command.get(command, 0) + 1
    for event in drifts:
        dtype = drift_type_fn(event)
        drift_by_type[dtype] = drift_by_type.get(dtype, 0) + 1
        if dtype == "missing_drift_type":
            unclassified_drifts += 1
    rows = sorted(
        [
            DriftRow(
                ts=event_ts_fn(event),
                drift_type=drift_type_fn(event),
                command=str(event.get("command", "")).strip() or "unknown",
                status=str(event.get("status", "")).strip() or "unknown",
                fingerprint_short=(
                    str(event.get("artifact_fingerprint", "")).strip()[:8]
                ),
                cause=drift_cause_fn(event),
            )
            for event in drifts
        ],
        key=lambda item: ts_sort_key_fn(item.ts),
        reverse=True,
    )[:top]
    # Token metrics are scoped to parent governance.ask invocations: phase
    # sub-events and non-LLM events never carry tokens, so counting them as
    # "missing" misreports telemetry coverage.
    invocations = [event for event in events if _is_ask_invocation(event)]
    total_in, total_out, with_tokens = _token_totals(invocations)
    ratio = (total_out / total_in) if total_in > 0 else 0.0
    return {
        "drifts": drifts,
        "events_by_command": events_by_command,
        "drift_by_type": drift_by_type,
        "unclassified_drifts": unclassified_drifts,
        "rows": rows,
        "total_in": total_in,
        "total_out": total_out,
        "ratio": ratio,
        "ask_invocations": len(invocations),
        "ask_events": len(ask_events),
        "missing_tokens": len(invocations) - with_tokens,
        "with_tokens": with_tokens,
        "non_token_events": len(events) - len(invocations),
    }


def default_events_path(*, resolve_workspace_root_fn: Any) -> Path:
    override = resolve_compliance_log_override()
    if override.path is not None:
        return override.path
    try:
        root = resolve_workspace_root_fn()
    except Exception:
        root = Path.cwd()
    return Path(root) / ".providence" / "runtime" / "compliance-events.jsonl"
