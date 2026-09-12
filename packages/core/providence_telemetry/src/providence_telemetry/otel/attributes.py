"""Converts providence_telemetry runtime events to OTel semantic-convention attribute dicts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from providence_telemetry.constants import (
    DEFAULT_SERVICE_NAME,
    DEFAULT_SERVICE_VERSION,
    SDD_NAMESPACE,
    SEVERITY_NUMBER,
)

from .constants import (
    EVENT_DOMAIN_KEY,
    EVENT_DOMAIN_VALUE,
    EVENT_NAME_KEY,
    EVENT_TIME_KEY,
    LOG_SEVERITY_KEY,
    LOG_SEVERITY_NUMBER_KEY,
    SDD_EVENT_TIMESTAMP_KEY,
    SDD_EVENT_TYPE_KEY,
    SERVICE_NAME_KEY,
    SERVICE_VERSION_KEY,
    SPAN_ID_KEY,
    TRACE_ID_KEY,
)


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_scalar(value: Any) -> str | int | float | bool:
    if isinstance(value, str | int | float | bool):
        return value
    if value is None:
        # OTel attributes cannot be None; "null" is the canonical string sentinel.
        return "null"
    return str(value)


def to_otel_attributes(
    event: dict[str, Any],
    *,
    service_name: str = DEFAULT_SERVICE_NAME,
    service_version: str = DEFAULT_SERVICE_VERSION,
    trace_id: str | None = None,
    span_id: str | None = None,
) -> dict[str, str | int | float | bool]:
    """Convert a runtime event to OTel-compatible attributes.

    Applies OTel semantic conventions:
      service.*  — resource semantics
      event.*    — event semantics
      log.*      — log semantics
      sdd.*      — SDD domain namespace
    """
    event_type = str(event.get("type", "unknown"))
    severity = str(event.get("severity", "INFO")).upper()
    ts = event.get("timestamp")
    timestamp = str(ts) if isinstance(ts, str) and ts != "" else _iso_utc_now()

    attrs: dict[str, str | int | float | bool] = {
        SERVICE_NAME_KEY: service_name,
        SERVICE_VERSION_KEY: service_version,
        EVENT_NAME_KEY: event_type,
        EVENT_DOMAIN_KEY: EVENT_DOMAIN_VALUE,
        EVENT_TIME_KEY: timestamp,
        LOG_SEVERITY_KEY: severity,
        LOG_SEVERITY_NUMBER_KEY: SEVERITY_NUMBER.get(severity, 9),
        SDD_EVENT_TYPE_KEY: event_type,
        SDD_EVENT_TIMESTAMP_KEY: timestamp,
    }

    if trace_id:
        attrs[TRACE_ID_KEY] = trace_id
    if span_id:
        attrs[SPAN_ID_KEY] = span_id

    for key, value in event.items():
        if key in {"type", "timestamp", "severity"}:
            continue
        clean_key = key[len(SDD_NAMESPACE) :] if key.startswith(SDD_NAMESPACE) else key
        attrs[f"{SDD_NAMESPACE}{clean_key}"] = _to_scalar(value)

    return attrs
