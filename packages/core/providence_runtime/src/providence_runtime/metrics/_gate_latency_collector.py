"""Gate-latency collector — aggregates `guardrail.gate.latency` events.

T-IMPL-2 (`.analysis/refined/20260825-tp4-instrumentation-design/design.md`
§ Gate-Latency Event Shape and § Collector Decision). Deliberately a separate
module from `_ask_latency_collector.py`: that collector's `ingest()` is
hard-scoped to `governance.ask.phase` events and an ask-specific
`(phase_id, latency_domain, path_id)` group key, neither of which applies to
gate-rule evaluations. Only the pure percentile math is shared (`_percentile`).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ._percentile import _percentile

if TYPE_CHECKING:
    from ..reader import TelemetryReader
    from ..telemetry import RuntimeEvent

_EVENT_NAME = "guardrail.gate.latency"


@dataclass(frozen=True)
class GateLatencyGroup:
    """Aggregated latency statistics for one grouping of gate evaluations."""

    count: int
    min_ms: int
    max_ms: int
    avg_ms: float
    p50_ms: int
    p95_ms: int


@dataclass(frozen=True)
class GateLatencySnapshot:
    """Point-in-time snapshot of aggregated gate-latency metrics.

    ``by_rule`` is the per-gate-rule P50/P95 view (grouped by ``rule_id`` —
    micro-policy 4's "gates síncronos possuem budget P50/P95"). ``pipeline``
    pools every rule's durations together into one group — the whole-request
    P50/P95 view (doc 06's `budgets.pr_pipeline` shape). Both are computed
    from the same underlying event stream; see design.md for why this is one
    event schema with two aggregation views rather than two instrumented
    call sites.
    """

    by_rule: dict[str, GateLatencyGroup] = field(default_factory=dict)
    pipeline: GateLatencyGroup | None = None


class GateLatencyCollector:
    """Aggregates `guardrail.gate.latency` events by `details.rule_id`.

    Thread-safe; uses a single RLock for all mutations. Can be populated from
    a TelemetryReader (JSONL replay) or by calling ingest(event) on each live
    RuntimeEvent.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._durations_by_rule: dict[str, list[int]] = {}

    def ingest(self, event: RuntimeEvent | dict[str, Any]) -> None:
        """Update internal duration lists from a single RuntimeEvent or dict.

        No-op on irrelevant event types or events missing ``duration_ms``.
        Acquires lock for all mutations.

        Parameters
        ----------
        event:
            A RuntimeEvent or dict representation (e.g., from JSONL). Must have
            fields: event, duration_ms, details (dict with rule_id).
        """
        event_dict = event.to_dict() if hasattr(event, "to_dict") else event

        if event_dict.get("event") != _EVENT_NAME:
            return

        duration_ms = event_dict.get("duration_ms")
        if duration_ms is None:
            return

        details = event_dict.get("details") or {}
        rule_id = details.get("rule_id") or "unknown"

        with self._lock:
            self._durations_by_rule.setdefault(rule_id, []).append(int(duration_ms))

    @classmethod
    def from_reader(cls, reader: TelemetryReader) -> GateLatencyCollector:
        """Build a collector by replaying all guardrail.gate.latency events from a TelemetryReader.

        Parameters
        ----------
        reader:
            An initialized TelemetryReader pointing to a JSONL events file.

        Returns
        -------
        GateLatencyCollector with aggregated state from all matching events.
        """
        collector = cls()
        for evt in reader.list_events():
            collector.ingest(evt)
        return collector

    def snapshot(self) -> GateLatencySnapshot:
        """Return a copy of the current aggregated state.

        Thread-safe; acquires lock for the entire copy operation.

        Returns
        -------
        GateLatencySnapshot with point-in-time values. Safe to share/serialize.
        """
        with self._lock:
            by_rule: dict[str, GateLatencyGroup] = {}
            pooled: list[int] = []
            for rule_id, values in self._durations_by_rule.items():
                sorted_values = sorted(values)
                by_rule[rule_id] = _group_from_sorted(sorted_values)
                pooled.extend(values)
            pipeline = _group_from_sorted(sorted(pooled)) if pooled else None
            return GateLatencySnapshot(by_rule=by_rule, pipeline=pipeline)

    def reset(self) -> None:
        """Reset all accumulated durations."""
        with self._lock:
            self._durations_by_rule.clear()


def _group_from_sorted(sorted_values: list[int]) -> GateLatencyGroup:
    return GateLatencyGroup(
        count=len(sorted_values),
        min_ms=sorted_values[0],
        max_ms=sorted_values[-1],
        avg_ms=sum(sorted_values) / len(sorted_values),
        p50_ms=_percentile(sorted_values, 50),
        p95_ms=_percentile(sorted_values, 95),
    )
