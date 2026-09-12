"""OTEL mapping layer — §13 Phase C opt-in OpenTelemetry bridge.

This module is zero-dependency by default.  The ``OtlpHttpExporter`` uses only
stdlib ``urllib.request`` so no additional packages are required.  If the
caller prefers the official ``opentelemetry-sdk``, they can implement the
``OtelExporter`` protocol and pass it to ``OtelBridge``.

Architecture
------------
::

    RuntimeEvent
        │
        ▼
    OtelAttributes.from_event()          ← pure mapping, no I/O
        │
        ▼
    OtelExporter.export(event, attrs)    ← transport abstraction
        │
    OtlpHttpExporter                     ← stdlib urllib, OTLP JSON format

``OtelBridge`` wraps ``TelemetrySink`` and calls the exporter on every
``emit()``.  The JSONL sink is always written first; OTEL export is
best-effort.  If the exporter raises, the event is silently dropped on the
OTEL side — JSONL remains the source of truth.

Usage example
-------------
::

    from providence_runtime import OtelBridge
    from providence_runtime.otel import OtlpHttpExporter

    exporter = OtlpHttpExporter(
        endpoint="https://api.datadoghq.com/api/v0.2/traces",
        headers={"DD-API-KEY": "..."},
    )
    sink = OtelBridge(exporter=exporter, jsonl_path=Path(".providence/runtime/events.jsonl"))
    sink.emit(RuntimeEvent(event="governance.compile", command="compile", ...))
"""

from __future__ import annotations

from ._exporter_protocol import OtelExporter
from ._otlp_http_exporter import OtlpHttpExporter
from ._payload import _build_otlp_payload, _status_code, _to_kv_list, _ts_to_nano

__all__ = [
    "OtelExporter",
    "OtlpHttpExporter",
    "_build_otlp_payload",
    "_status_code",
    "_to_kv_list",
    "_ts_to_nano",
]
