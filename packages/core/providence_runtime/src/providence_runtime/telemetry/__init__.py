"""Telemetry engine — typed runtime events with optional JSONL persistence.

Event schema is aligned with the Datadog-inspired envelope defined in §13.3
of the improvement plan.  The canonical audit sink is the JSONL file at
``.providence/runtime/compliance-events.jsonl``; the sink path is caller-supplied so
the package remains zero-dependency.
"""

from __future__ import annotations

from .._events import (  # noqa: F401 — re-exported for backward compat
    EVENT_SCHEMA_VERSION,
    OtelAttributes,
    RuntimeEvent,
)
from ._constants import (
    _MANDATORY_EVENTS,
    _PATH_BUDGET_BYTES,
    _ZONE_BREACH_PCT,
    _ZONE_RED_PCT,
    ECONOMY_BUDGET_BREACH,
    ECONOMY_BUDGET_WARN,
    ECONOMY_COMPRESSION_SKIP,
    ECONOMY_RETRY_CAP_REACHED,
    MODE_ACTIVE,
    MODE_PASSIVE,
    MODE_STRICT,
)
from ._factory import create_sink, get_otel_endpoint
from ._otel_bridge import OtelBridge
from ._sink import TelemetrySink

__all__ = [
    "EVENT_SCHEMA_VERSION",
    "RuntimeEvent",
    "TelemetrySink",
    "OtelAttributes",
    "OtelBridge",
    "create_sink",
    "get_otel_endpoint",
    "MODE_PASSIVE",
    "MODE_ACTIVE",
    "MODE_STRICT",
    "ECONOMY_BUDGET_WARN",
    "ECONOMY_BUDGET_BREACH",
    "ECONOMY_COMPRESSION_SKIP",
    "ECONOMY_RETRY_CAP_REACHED",
    "_MANDATORY_EVENTS",
    "_PATH_BUDGET_BYTES",
    "_ZONE_BREACH_PCT",
    "_ZONE_RED_PCT",
]
