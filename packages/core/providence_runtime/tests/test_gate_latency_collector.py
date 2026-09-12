"""Tests for GateLatencyCollector — guardrail.gate.latency aggregation (T-IMPL-2).

Percentile method: linear interpolation between closest ranks (shared with
AskLatencyCollector via `providence_runtime.metrics._percentile`). See that
module's docstring for the formula and worked examples.
"""

from __future__ import annotations

from providence_runtime.metrics import GateLatencyCollector


def _gate_event(rule_id, duration_ms):
    return {
        "event": "guardrail.gate.latency",
        "duration_ms": duration_ms,
        "details": {"rule_id": rule_id, "outcome": "deny" if rule_id else "allow"},
    }


def test_ingest_ignores_other_event_types():
    collector = GateLatencyCollector()
    collector.ingest({"event": "runtime.skill.run", "duration_ms": 100})
    snapshot = collector.snapshot()
    assert snapshot.by_rule == {}
    assert snapshot.pipeline is None


def test_ingest_ignores_events_without_duration():
    collector = GateLatencyCollector()
    collector.ingest({"event": "guardrail.gate.latency", "details": {"rule_id": "x"}})
    snapshot = collector.snapshot()
    assert snapshot.by_rule == {}


def test_snapshot_groups_by_rule_id():
    collector = GateLatencyCollector()
    collector.ingest(_gate_event("scope_violation", 10))
    collector.ingest(_gate_event("scope_violation", 30))
    collector.ingest(_gate_event("default_allow", 5))
    snapshot = collector.snapshot()
    assert set(snapshot.by_rule) == {"scope_violation", "default_allow"}
    assert snapshot.by_rule["scope_violation"].count == 2
    assert snapshot.by_rule["scope_violation"].min_ms == 10
    assert snapshot.by_rule["scope_violation"].max_ms == 30
    assert snapshot.by_rule["default_allow"].count == 1


def test_snapshot_pipeline_pools_every_rule():
    collector = GateLatencyCollector()
    collector.ingest(_gate_event("scope_violation", 10))
    collector.ingest(_gate_event("default_allow", 20))
    collector.ingest(_gate_event("default_allow", 30))
    snapshot = collector.snapshot()
    assert snapshot.pipeline is not None
    assert snapshot.pipeline.count == 3
    assert snapshot.pipeline.min_ms == 10
    assert snapshot.pipeline.max_ms == 30
    # Per-rule view stays distinct from the pooled pipeline view.
    assert snapshot.by_rule["default_allow"].count == 2


def test_ingest_defaults_missing_rule_id_to_unknown():
    collector = GateLatencyCollector()
    collector.ingest(
        {"event": "guardrail.gate.latency", "duration_ms": 7, "details": {}}
    )
    snapshot = collector.snapshot()
    assert "unknown" in snapshot.by_rule
    assert snapshot.pipeline.count == 1


def test_percentiles_match_shared_percentile_helper():
    # Hand-computed (linear interpolation between closest ranks), same
    # formula validated in test_ask_latency_collector.py.
    # values = [10, 20, 30, 40, 100], n=5
    #   p50: k = (5-1)*0.50 = 2.0 -> exact index 2 -> 30
    #   p95: k = (5-1)*0.95 = 3.8 -> f=3 (40), c=4 (100)
    #        -> 40*(4-3.8) + 100*(3.8-3) = 8 + 80 = 88
    collector = GateLatencyCollector()
    for value in (10, 20, 30, 40, 100):
        collector.ingest(_gate_event("default_allow", value))
    group = collector.snapshot().by_rule["default_allow"]
    assert group.p50_ms == 30
    assert group.p95_ms == 88


def test_reset_clears_accumulated_state():
    collector = GateLatencyCollector()
    collector.ingest(_gate_event("default_allow", 10))
    collector.reset()
    snapshot = collector.snapshot()
    assert snapshot.by_rule == {}
    assert snapshot.pipeline is None
