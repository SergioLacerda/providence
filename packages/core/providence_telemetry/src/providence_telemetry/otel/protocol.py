"""OtelExporter Protocol — the structural contract for pluggable OTel backends."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class OtelExporter(Protocol):
    """Plugin contract for OTel backends.

    Implement this Protocol to integrate any OpenTelemetry backend
    without inheriting from providence_telemetry internals.
    """

    def export_event(
        self,
        attributes: dict[str, str | int | float | bool],
        *,
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> None:
        """Send a single telemetry event with the given OTel attributes."""
        pass

    def shutdown(self) -> None:
        """Flush and release any resources held by the exporter."""
        pass
