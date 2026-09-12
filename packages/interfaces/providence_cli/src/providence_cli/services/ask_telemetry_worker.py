"""Async telemetry flush worker and canonical event routing for ask command flows."""

from __future__ import annotations

import atexit
import json
import queue
import threading
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any, Protocol, cast

from providence_runtime import (
    OtelBridge,
    RuntimeEvent,
    TelemetrySink,
    get_otel_endpoint,
)
from providence_runtime.otel import OtlpHttpExporter

from providence_cli.services._ask_telemetry_support import build_sink
from providence_cli.utils.telemetry_paths import resolve_compliance_events_path
from providence_core.output.canonical_event import CanonicalLogEvent, ProfileRenderer

_TELEMETRY_LEVELS = ("debug", "trace")


class _EventSink(Protocol):
    def emit(self, event: RuntimeEvent) -> None:
        pass


def build_ask_telemetry_sink(
    workspace_root: Path,
    *,
    telemetry_sink_cls: type[TelemetrySink] = TelemetrySink,
    otel_bridge_cls: type[OtelBridge] = OtelBridge,
    otlp_exporter_cls: type[OtlpHttpExporter] = OtlpHttpExporter,
) -> _EventSink:
    """Build one telemetry sink to be reused across every event in a single
    `providence ask` call.

    Each `emit_ask_telemetry` call previously built (and flushed) its own
    sink  up to 6-7 per call (one parent + one per recorded phase), each
    triggering its own background flush. Building one sink up front and
    passing it into every `emit_ask_telemetry` call (with `flush=False`),
    then flushing once at the end, collapses that into a single flush per
    call without changing event content (design.md D4).
    """
    events_path = resolve_compliance_events_path(workspace_root=workspace_root)
    otel_endpoint = get_otel_endpoint()
    return cast(
        _EventSink,
        build_sink(
            otel_endpoint=otel_endpoint,
            events_path=events_path,
            telemetry_sink_cls=telemetry_sink_cls,
            otel_bridge_cls=otel_bridge_cls,
            otlp_exporter_cls=otlp_exporter_cls,
        ),
    )


def route_canonical_event(
    event: CanonicalLogEvent, *, renderer: ProfileRenderer | None = None
) -> str:
    """Route a canonical event per M020.

    `level=debug` and `level=trace` events always emit structured JSON via
    `to_telemetry_dict()`, bypassing the profile renderer. Other levels are
    rendered through `ProfileRenderer.render()` (compact `simple_output()`).
    """
    if event.level in _TELEMETRY_LEVELS:
        return json.dumps(event.to_telemetry_dict())
    return (renderer or ProfileRenderer()).render(event)


_TELEMETRY_QUEUE: queue.Queue[Callable[[], None] | None] = queue.Queue()


def _telemetry_worker() -> None:
    while True:
        callback = _TELEMETRY_QUEUE.get()
        if callback is None:
            break
        with suppress(Exception):
            callback()


_TELEMETRY_WORKER = threading.Thread(target=_telemetry_worker, daemon=True)
_TELEMETRY_WORKER.start()


def _shutdown_telemetry_worker() -> None:
    _TELEMETRY_QUEUE.put(None)
    _TELEMETRY_WORKER.join(timeout=2)


atexit.register(_shutdown_telemetry_worker)


def enqueue_flush(sink: Any) -> None:
    """Flush telemetry asynchronously when the sink exposes a flush method."""
    flush = getattr(sink, "flush", None)
    if callable(flush):
        _TELEMETRY_QUEUE.put(flush)
