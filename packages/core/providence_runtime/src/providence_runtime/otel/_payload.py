"""OTLP/JSON payload-building helpers — pure functions, no I/O."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .._events import OtelAttributes, RuntimeEvent


def _ts_to_nano(ts: str) -> int:
    """Convert an ISO-8601 string to Unix nanoseconds.  Returns 0 on failure."""
    if not ts:
        return 0
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1_000_000_000)
    except Exception:
        return 0


def _status_code(status: str) -> int:
    """Map an SDD status string to an OTLP span status code integer."""
    return {"ok": 1, "warn": 1, "fail": 2}.get(status.lower(), 0)


def _to_kv_list(attrs: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a flat dict to the OTLP ``KeyValue`` list format."""
    result: list[dict[str, Any]] = []
    for key, value in attrs.items():
        if isinstance(value, bool):
            result.append({"key": key, "value": {"boolValue": value}})
        elif isinstance(value, int):
            result.append({"key": key, "value": {"intValue": value}})
        elif isinstance(value, float):
            result.append({"key": key, "value": {"doubleValue": value}})
        else:
            result.append({"key": key, "value": {"stringValue": str(value)}})
    return result


def _build_otlp_payload(event: RuntimeEvent, attrs: OtelAttributes) -> dict[str, Any]:
    """Build a minimal OTLP/JSON resourceSpans payload for a single span."""
    start_ns = _ts_to_nano(event.ts)
    end_ts = event.end_ts if event.end_ts else event.ts
    end_ns = _ts_to_nano(end_ts)

    span: dict[str, Any] = {
        "traceId": attrs.trace_id,
        "spanId": attrs.span_id,
        "name": attrs.sdd_event,
        "kind": 1,  # SPAN_KIND_INTERNAL
        "startTimeUnixNano": start_ns,
        "endTimeUnixNano": end_ns,
        "attributes": _to_kv_list(attrs.to_otel_dict()),
        "status": {
            "code": _status_code(attrs.sdd_status),
        },
    }
    if attrs.sdd_parent_event_id:
        # TEL-08 (`.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`):
        # `sdd_parent_event_id` is populated with the parent RuntimeEvent's
        # own `span_id` (see `_pipeline_runtime_telemetry.py`) — it is
        # already a valid OTLP span id, not a separate identifier scheme.
        # Mapping it to the native `parentSpanId` field lets a real
        # collector reconstruct the span tree; the `sdd.parent_event_id`
        # attribute (in `attributes` above) is kept for backward-compatible
        # correlation by anything already reading it.
        span["parentSpanId"] = attrs.sdd_parent_event_id

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": _to_kv_list({"service.name": attrs.service_name}),
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "providence-runtime", "version": "1.0"},
                        "spans": [span],
                    }
                ],
            }
        ]
    }
