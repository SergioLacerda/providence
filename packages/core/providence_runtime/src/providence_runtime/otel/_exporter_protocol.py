"""OtelExporter protocol — implement to add any OTEL-compatible backend."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .._events import OtelAttributes, RuntimeEvent


@runtime_checkable
class OtelExporter(Protocol):
    """Minimal transport protocol for OTEL event export."""

    def export(self, event: RuntimeEvent, attrs: OtelAttributes) -> None:
        """Export a single event with its OTEL-mapped attributes."""
        pass

    def shutdown(self) -> None:
        """Release resources (connections, buffers, etc.)."""
        pass
