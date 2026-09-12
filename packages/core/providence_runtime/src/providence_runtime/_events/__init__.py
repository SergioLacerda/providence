"""Shared event data structures — isolated to break cyclic imports.

Extracted from telemetry.py to allow alerts.py to import RuntimeEvent
without creating a telemetry ↔ alerts cycle.
"""

from __future__ import annotations

from ._otel_attributes import OtelAttributes
from ._runtime_event import (
    EVENT_SCHEMA_VERSION,
    RuntimeEvent,
    _generate_span_id,
    _utc_now,
)

__all__ = [
    "EVENT_SCHEMA_VERSION",
    "OtelAttributes",
    "RuntimeEvent",
    "_generate_span_id",
    "_utc_now",
]
