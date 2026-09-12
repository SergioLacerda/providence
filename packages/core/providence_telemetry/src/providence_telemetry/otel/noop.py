"""No-op OTel exporter that silently discards all events."""

from __future__ import annotations


class NoopExporter:
    """Default OTel exporter — drops all events silently.

    Safe out-of-the-box default. Replace with a real exporter
    by implementing the OtelExporter Protocol.
    """

    def export_event(
        self,
        attributes: dict[str, str | int | float | bool],
        *,
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> None:
        """Accept and discard an event — no-op implementation."""

    def shutdown(self) -> None:
        """No-op shutdown."""
