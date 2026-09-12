"""Ask phase-latency collector — aggregates governance.ask.phase events.

Kept separate from TokenEconomyCollector per the trace-route design's
"Recommended Ownership" decision: governance latency and token/budget/retry
economy are distinct metric domains.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ._percentile import _percentile

if TYPE_CHECKING:
    from ..reader import TelemetryReader
    from ..telemetry import RuntimeEvent


@dataclass(frozen=True)
class LatencyGroup:
    """Aggregated latency statistics for one (phase_id, latency_domain, path_id) group."""

    count: int
    min_ms: int
    max_ms: int
    avg_ms: float
    p50_ms: int
    p95_ms: int


@dataclass(frozen=True)
class AskLatencySnapshot:
    """Point-in-time snapshot of aggregated ask-phase latency metrics.

    Thread-safe snapshot captured from AskLatencyCollector.snapshot().
    Keyed by (phase_id, latency_domain, path_id).
    """

    groups: dict[tuple[str, str, str], LatencyGroup] = field(default_factory=dict)


class AskLatencyCollector:
    """Aggregates `governance.ask.phase` events by (phase_id, latency_domain, path_id).

    Thread-safe; uses a single RLock for all mutations. Can be populated from
    a TelemetryReader (JSONL replay) or by calling ingest(event) on each live
    RuntimeEvent.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._durations: dict[tuple[str, str, str], list[int]] = {}

    def ingest(self, event: RuntimeEvent | dict[str, Any]) -> None:
        """Update internal duration lists from a single RuntimeEvent or dict.

        No-op on irrelevant event types or events missing ``duration_ms``.
        Acquires lock for all mutations.

        Parameters
        ----------
        event:
            A RuntimeEvent or dict representation (e.g., from JSONL). Must have
            fields: event, duration_ms, path_id, details (dict with phase_id /
            latency_domain).
        """
        event_dict = event.to_dict() if hasattr(event, "to_dict") else event

        if event_dict.get("event") != "governance.ask.phase":
            return

        duration_ms = event_dict.get("duration_ms")
        if duration_ms is None:
            return

        details = event_dict.get("details") or {}
        phase_id = details.get("phase_id", "unknown")
        latency_domain = details.get("latency_domain", "unknown")
        path_id = event_dict.get("path_id") or "unknown"

        key = (phase_id, latency_domain, path_id)
        with self._lock:
            self._durations.setdefault(key, []).append(int(duration_ms))

    @classmethod
    def from_reader(cls, reader: TelemetryReader) -> AskLatencyCollector:
        """Build a collector by replaying all governance.ask.phase events from a TelemetryReader.

        Parameters
        ----------
        reader:
            An initialized TelemetryReader pointing to a JSONL events file.

        Returns
        -------
        AskLatencyCollector with aggregated state from all matching events.
        """
        collector = cls()
        for evt in reader.list_events():
            collector.ingest(evt)
        return collector

    def snapshot(self) -> AskLatencySnapshot:
        """Return a copy of the current aggregated state.

        Thread-safe; acquires lock for the entire copy operation.

        Returns
        -------
        AskLatencySnapshot with point-in-time values. Safe to share/serialize.
        """
        with self._lock:
            groups: dict[tuple[str, str, str], LatencyGroup] = {}
            for key, values in self._durations.items():
                sorted_values = sorted(values)
                groups[key] = LatencyGroup(
                    count=len(sorted_values),
                    min_ms=sorted_values[0],
                    max_ms=sorted_values[-1],
                    avg_ms=sum(sorted_values) / len(sorted_values),
                    p50_ms=_percentile(sorted_values, 50),
                    p95_ms=_percentile(sorted_values, 95),
                )
            return AskLatencySnapshot(groups=groups)

    def reset(self) -> None:
        """Reset all accumulated durations."""
        with self._lock:
            self._durations.clear()
