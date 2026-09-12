"""OtelBridge — TelemetrySink subclass with opt-in OTEL export."""

from __future__ import annotations

import contextlib
import uuid
from typing import Any

from .._events import OtelAttributes, RuntimeEvent
from ._sink import TelemetrySink


class OtelBridge(TelemetrySink):
    """A ``TelemetrySink`` that additionally exports events via OTEL.

    Parameters
    ----------
    exporter:
        An ``OtelExporter`` instance.  Pass ``None`` to disable OTEL export
        (bridge becomes a transparent ``TelemetrySink`` pass-through).
    **kwargs:
        Forwarded to ``TelemetrySink.__init__()`` (``jsonl_path``,
        ``logging_mode``, ``segment_by_work_item``).
    """

    def __init__(
        self,
        exporter: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._exporter = exporter

    def emit(self, event: RuntimeEvent) -> None:
        """Persist event to JSONL then export to OTEL (best-effort)."""
        super().emit(event)
        if self._exporter is None:
            return

        span_id = event.span_id or uuid.uuid4().hex[:16]
        attrs = OtelAttributes.from_event(event, span_id=span_id)
        # OTEL export is best-effort; JSONL is source of truth
        with contextlib.suppress(Exception):
            self._exporter.export(event, attrs)

    def shutdown(self) -> None:
        """Shut down the exporter and release any held resources."""
        if self._exporter is not None:
            with contextlib.suppress(Exception):
                self._exporter.shutdown()
