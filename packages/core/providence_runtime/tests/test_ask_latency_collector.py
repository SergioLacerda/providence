"""Tests for AskLatencyCollector — governance.ask.phase aggregation.

Percentile method: linear interpolation between closest ranks (matching
numpy's default `np.percentile`). See `_percentile()` docstring in
`providence_runtime.metrics._ask_latency_collector` for the formula and worked
examples; the test cases below re-derive the same numbers by hand before
asserting on them.
"""

from __future__ import annotations

from providence_runtime.metrics._ask_latency_collector import AskLatencyCollector
from tests.helpers.text_io import write_text_utf8


def _phase_event(phase_id, latency_domain, duration_ms, path_id="PATH_A"):
    return {
        "event": "governance.ask.phase",
        "duration_ms": duration_ms,
        "path_id": path_id,
        "details": {"phase_id": phase_id, "latency_domain": latency_domain},
    }


def test_ingest_ignores_non_phase_events():
    collector = AskLatencyCollector()
    collector.ingest({"event": "governance.ask", "duration_ms": 100})
    snapshot = collector.snapshot()
    assert snapshot.groups == {}


def test_ingest_aggregates_by_phase_id():
    collector = AskLatencyCollector()
    collector.ingest(_phase_event("ask.governance.snapshot", "governance", 50))
    collector.ingest(_phase_event("ask.governance.snapshot", "governance", 70))
    snapshot = collector.snapshot()
    group = snapshot.groups[("ask.governance.snapshot", "governance", "PATH_A")]
    assert group.count == 2
    assert group.min_ms == 50
    assert group.max_ms == 70
    assert group.avg_ms == 60


def test_percentiles_odd_count():
    # Hand-computed (linear interpolation between closest ranks):
    # values = [10, 20, 30, 40, 100], n=5
    #   p50: k = (5-1)*0.50 = 2.0 -> exact index 2 -> 30
    #   p95: k = (5-1)*0.95 = 3.8 -> f=3 (40), c=4 (100)
    #        -> 40*(4-3.8) + 100*(3.8-3) = 8 + 80 = 88
    collector = AskLatencyCollector()
    for ms in [10, 20, 30, 40, 100]:
        collector.ingest(_phase_event("ask.response.render", "rendering", ms))
    group = collector.snapshot().groups[("ask.response.render", "rendering", "PATH_A")]
    assert group.count == 5
    assert group.p50_ms == 30
    assert group.p95_ms == 88
    assert group.p95_ms >= group.p50_ms


def test_percentiles_even_count():
    # Hand-computed (linear interpolation between closest ranks):
    # values = [10, 20, 30, 40], n=4
    #   p50: k = (4-1)*0.50 = 1.5 -> f=1 (20), c=2 (30)
    #        -> 20*(2-1.5) + 30*(1.5-1) = 10 + 15 = 25
    #   p95: k = (4-1)*0.95 = 2.85 -> f=2 (30), c=3 (40)
    #        -> 30*(3-2.85) + 40*(2.85-2) = 4.5 + 34 = 38.5 -> round() = 38
    #        (Python's round() uses banker's rounding: round(38.5) == 38)
    collector = AskLatencyCollector()
    for ms in [10, 20, 30, 40]:
        collector.ingest(_phase_event("ask.cli.entry", "local_cli", ms))
    group = collector.snapshot().groups[("ask.cli.entry", "local_cli", "PATH_A")]
    assert group.count == 4
    assert group.p50_ms == 25
    assert group.p95_ms == 38


def test_from_reader_replays_events(tmp_path):
    from providence_runtime.reader import TelemetryReader

    events_path = tmp_path / "events.jsonl"
    write_text_utf8(
        events_path,
        '{"event": "governance.ask.phase", "duration_ms": 15, "path_id": "PATH_B", '
        '"details": {"phase_id": "ask.workspace.resolve", "latency_domain": "local_fs"}}\n'
        '{"event": "governance.ask", "duration_ms": 999}\n',
    )
    reader = TelemetryReader(events_path)
    collector = AskLatencyCollector.from_reader(reader)
    snapshot = collector.snapshot()
    assert snapshot.groups[("ask.workspace.resolve", "local_fs", "PATH_B")].count == 1
    assert len(snapshot.groups) == 1


def test_reset_clears_state():
    collector = AskLatencyCollector()
    collector.ingest(_phase_event("ask.cli.entry", "local_cli", 5))
    collector.reset()
    assert collector.snapshot().groups == {}


def test_ingest_skips_events_missing_duration_ms():
    collector = AskLatencyCollector()
    event = {
        "event": "governance.ask.phase",
        "path_id": "PATH_A",
        "details": {"phase_id": "ask.cli.entry", "latency_domain": "local_cli"},
    }
    # Should not raise, and should not create a group.
    collector.ingest(event)
    event_with_none = dict(event, duration_ms=None)
    collector.ingest(event_with_none)
    assert collector.snapshot().groups == {}


def test_ingest_defaults_missing_details_and_path_id():
    collector = AskLatencyCollector()
    collector.ingest({"event": "governance.ask.phase", "duration_ms": 12})
    snapshot = collector.snapshot()
    assert snapshot.groups[("unknown", "unknown", "unknown")].count == 1
