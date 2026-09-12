"""Cognitive entropy scoring tests — Phase 4.

Covers:
  - EntropyScore.compute() formula: retry_count * reflection_count * budget_utilization_pct / 100
  - Zero-retry / zero-reflection edge cases (score = 0)
  - Theoretical maxima per PATH A/B/C/D
  - EntropyAdvisor threshold logic: strict greater-than (at-threshold is NOT a breach)
  - PATH-specific thresholds (A/D=1.0, B/C=3.0); unknown → conservative 1.0
  - DecompositionSuggestion reason messages contain score and path info
  - ConvergenceTracker: insufficient samples, flat, growing, decreasing trends
  - ConvergenceTracker window limits to last N samples
  - SessionDriftScorer: from_events(), from_jsonl(), overload detection
  - Heavy-path overloading (C/D > 50%), light-path dominance (no overload)
  - Missing/empty path_id ignored in drift distribution
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from providence_runtime.entropy import (
    _DEFAULT_ENTROPY_THRESHOLD,
    _DIVERGENCE_SLOPE_THRESHOLD,
    _PATH_ENTROPY_THRESHOLD,
    ConvergenceTracker,
    EntropyAdvisor,
    EntropyScore,
    SessionDriftScorer,
)

# ---------------------------------------------------------------------------
# EntropyScore.compute()
# ---------------------------------------------------------------------------


class TestEntropyScore:
    def test_formula_basic(self) -> None:
        # 2 * 1 * 90.0 / 100 = 1.8
        s = EntropyScore.compute(
            retry_count=2, reflection_count=1, budget_utilization_pct=90.0
        )
        assert s.score == pytest.approx(1.8)

    def test_zero_retries_gives_zero_score(self) -> None:
        s = EntropyScore.compute(
            retry_count=0, reflection_count=2, budget_utilization_pct=95.0
        )
        assert s.score == 0.0

    def test_zero_reflections_gives_zero_score(self) -> None:
        s = EntropyScore.compute(
            retry_count=3, reflection_count=0, budget_utilization_pct=95.0
        )
        assert s.score == 0.0

    def test_max_path_a_score(self) -> None:
        # PATH A ceiling: retry=2, reflection=1 → 2 * 1 * 100 / 100 = 2.0
        s = EntropyScore.compute(
            retry_count=2, reflection_count=1, budget_utilization_pct=100.0, path_id="A"
        )
        assert s.score == pytest.approx(2.0)

    def test_max_path_b_score(self) -> None:
        # PATH B ceiling: retry=3, reflection=2 → 3 * 2 * 100 / 100 = 6.0
        s = EntropyScore.compute(
            retry_count=3, reflection_count=2, budget_utilization_pct=100.0, path_id="B"
        )
        assert s.score == pytest.approx(6.0)

    def test_path_id_stored(self) -> None:
        s = EntropyScore.compute(
            retry_count=1, reflection_count=1, budget_utilization_pct=50.0, path_id="C"
        )
        assert s.path_id == "C"

    def test_unknown_path_id_stored(self) -> None:
        s = EntropyScore.compute(
            retry_count=1, reflection_count=1, budget_utilization_pct=50.0, path_id="Z"
        )
        assert s.path_id == "Z"

    def test_default_path_id_is_empty(self) -> None:
        s = EntropyScore.compute(
            retry_count=1, reflection_count=1, budget_utilization_pct=50.0
        )
        assert s.path_id == ""

    def test_all_fields_populated(self) -> None:
        s = EntropyScore.compute(
            retry_count=2, reflection_count=2, budget_utilization_pct=75.0, path_id="B"
        )
        assert s.retry_count == 2
        assert s.reflection_count == 2
        assert s.budget_utilization_pct == 75.0


# ---------------------------------------------------------------------------
# EntropyAdvisor
# ---------------------------------------------------------------------------


class TestEntropyAdvisor:
    def test_below_threshold_no_decompose(self) -> None:
        advisor = EntropyAdvisor()
        # score = 0 * 0 * 50 / 100 = 0; threshold A = 1.0
        suggestion = advisor.advise(
            retry_count=0, reflection_count=0, budget_utilization_pct=50.0, path_id="A"
        )
        assert not suggestion.should_decompose

    def test_at_threshold_no_decompose(self) -> None:
        """Score exactly equal to threshold must NOT trigger decomposition (strict >)."""
        advisor = EntropyAdvisor()
        # PATH A threshold = 1.0 → need score = 1.0 exactly: 2 * 1 * 50 / 100 = 1.0
        suggestion = advisor.advise(
            retry_count=2, reflection_count=1, budget_utilization_pct=50.0, path_id="A"
        )
        assert suggestion.entropy_score == pytest.approx(1.0)
        assert not suggestion.should_decompose

    def test_above_threshold_suggests_decompose(self) -> None:
        advisor = EntropyAdvisor()
        # PATH A threshold = 1.0 → score = 2 * 1 * 90 / 100 = 1.8 > 1.0
        suggestion = advisor.advise(
            retry_count=2, reflection_count=1, budget_utilization_pct=90.0, path_id="A"
        )
        assert suggestion.should_decompose

    def test_path_a_threshold(self) -> None:
        advisor = EntropyAdvisor()
        suggestion = advisor.advise(
            retry_count=2, reflection_count=1, budget_utilization_pct=90.0, path_id="A"
        )
        assert suggestion.threshold == _PATH_ENTROPY_THRESHOLD["A"]

    def test_path_b_threshold(self) -> None:
        advisor = EntropyAdvisor()
        suggestion = advisor.advise(
            retry_count=3, reflection_count=2, budget_utilization_pct=40.0, path_id="B"
        )
        assert suggestion.threshold == _PATH_ENTROPY_THRESHOLD["B"]

    def test_path_b_no_decompose_below_threshold(self) -> None:
        advisor = EntropyAdvisor()
        # PATH B threshold = 3.0 → score = 3 * 2 * 40 / 100 = 2.4 < 3.0
        suggestion = advisor.advise(
            retry_count=3, reflection_count=2, budget_utilization_pct=40.0, path_id="B"
        )
        assert not suggestion.should_decompose

    def test_path_b_decompose_above_threshold(self) -> None:
        advisor = EntropyAdvisor()
        # PATH B threshold = 3.0 → score = 3 * 2 * 60 / 100 = 3.6 > 3.0
        suggestion = advisor.advise(
            retry_count=3, reflection_count=2, budget_utilization_pct=60.0, path_id="B"
        )
        assert suggestion.should_decompose

    def test_unknown_path_uses_conservative_threshold(self) -> None:
        advisor = EntropyAdvisor()
        suggestion = advisor.advise(
            retry_count=2, reflection_count=1, budget_utilization_pct=90.0, path_id="Z"
        )
        assert suggestion.threshold == _DEFAULT_ENTROPY_THRESHOLD

    def test_suggestion_contains_score_in_reason(self) -> None:
        advisor = EntropyAdvisor()
        suggestion = advisor.advise(
            retry_count=2, reflection_count=1, budget_utilization_pct=90.0, path_id="A"
        )
        assert "1.80" in suggestion.reason

    def test_suggestion_contains_path_id_in_reason(self) -> None:
        advisor = EntropyAdvisor()
        suggestion = advisor.advise(
            retry_count=2, reflection_count=1, budget_utilization_pct=90.0, path_id="A"
        )
        assert "PATH A" in suggestion.reason

    def test_no_decompose_reason_says_within_threshold(self) -> None:
        advisor = EntropyAdvisor()
        suggestion = advisor.advise(
            retry_count=0, reflection_count=0, budget_utilization_pct=10.0, path_id="A"
        )
        assert "within threshold" in suggestion.reason

    def test_decompose_reason_says_exceeds_threshold(self) -> None:
        advisor = EntropyAdvisor()
        suggestion = advisor.advise(
            retry_count=2, reflection_count=1, budget_utilization_pct=90.0, path_id="A"
        )
        assert "exceeds threshold" in suggestion.reason

    def test_path_id_stored_in_suggestion(self) -> None:
        advisor = EntropyAdvisor()
        suggestion = advisor.advise(
            retry_count=1, reflection_count=1, budget_utilization_pct=50.0, path_id="C"
        )
        assert suggestion.path_id == "C"


# ---------------------------------------------------------------------------
# ConvergenceTracker
# ---------------------------------------------------------------------------


class TestConvergenceTracker:
    def test_no_samples_is_converging(self) -> None:
        tracker = ConvergenceTracker()
        report = tracker.report()
        assert report.is_converging
        assert report.samples == []

    def test_one_sample_is_converging(self) -> None:
        tracker = ConvergenceTracker()
        tracker.record(50.0)
        report = tracker.report()
        assert report.is_converging
        assert report.trend == pytest.approx(0.0)

    def test_flat_series_is_converging(self) -> None:
        tracker = ConvergenceTracker()
        for _ in range(3):
            tracker.record(60.0)
        report = tracker.report()
        assert report.is_converging
        assert report.trend == pytest.approx(0.0)

    def test_growing_series_not_converging(self) -> None:
        tracker = ConvergenceTracker()
        for pct in [50.0, 65.0, 80.0]:
            tracker.record(pct)
        report = tracker.report()
        assert not report.is_converging
        assert report.trend > _DIVERGENCE_SLOPE_THRESHOLD

    def test_decreasing_series_is_converging(self) -> None:
        tracker = ConvergenceTracker()
        for pct in [80.0, 65.0, 50.0]:
            tracker.record(pct)
        report = tracker.report()
        assert report.is_converging
        assert report.trend < 0.0

    def test_report_contains_samples(self) -> None:
        tracker = ConvergenceTracker()
        tracker.record(40.0)
        tracker.record(50.0)
        report = tracker.report()
        assert report.samples == [40.0, 50.0]

    def test_trend_positive_for_growing(self) -> None:
        tracker = ConvergenceTracker()
        for pct in [10.0, 50.0, 90.0]:
            tracker.record(pct)
        report = tracker.report()
        assert report.trend > 0.0

    def test_window_uses_last_n_samples(self) -> None:
        tracker = ConvergenceTracker(window=3)
        # First 3 samples are stable; last 3 show a big jump → should be diverging
        for pct in [50.0, 50.0, 50.0, 60.0, 75.0, 90.0]:
            tracker.record(pct)
        report = tracker.report()
        assert report.samples == [60.0, 75.0, 90.0]
        assert not report.is_converging

    def test_reason_mentions_threshold(self) -> None:
        tracker = ConvergenceTracker()
        tracker.record(10.0)
        tracker.record(12.0)
        report = tracker.report()
        assert str(_DIVERGENCE_SLOPE_THRESHOLD) in report.reason


# ---------------------------------------------------------------------------
# SessionDriftScorer
# ---------------------------------------------------------------------------


class _FakeEvent:
    def __init__(self, path_id: str) -> None:
        self.path_id = path_id


class TestSessionDriftScorer:
    def test_empty_events_no_overload(self) -> None:
        dist = SessionDriftScorer.from_events([])
        assert not dist.is_overloaded
        assert dist.total == 0
        assert dist.dominant_path == ""

    def test_distribution_counts_correct(self) -> None:
        events = [_FakeEvent("A"), _FakeEvent("A"), _FakeEvent("B"), _FakeEvent("C")]
        dist = SessionDriftScorer.from_events(events)
        assert dist.counts["A"] == 2
        assert dist.counts["B"] == 1
        assert dist.counts["C"] == 1
        assert dist.total == 4

    def test_heavy_path_dominant_is_overloaded(self) -> None:
        # PATH C at 3/4 = 75% > 50% threshold
        events = [_FakeEvent("C"), _FakeEvent("C"), _FakeEvent("C"), _FakeEvent("A")]
        dist = SessionDriftScorer.from_events(events)
        assert dist.is_overloaded
        assert dist.dominant_path == "C"

    def test_light_path_dominant_not_overloaded(self) -> None:
        # PATH A at 3/4 = 75% but A is not a heavy path
        events = [_FakeEvent("A"), _FakeEvent("A"), _FakeEvent("A"), _FakeEvent("B")]
        dist = SessionDriftScorer.from_events(events)
        assert not dist.is_overloaded
        assert dist.dominant_path == "A"

    def test_heavy_path_below_threshold_not_overloaded(self) -> None:
        # PATH C at 2/5 = 40% < 50% threshold
        events = [
            _FakeEvent("C"),
            _FakeEvent("C"),
            _FakeEvent("A"),
            _FakeEvent("A"),
            _FakeEvent("B"),
        ]
        dist = SessionDriftScorer.from_events(events)
        assert not dist.is_overloaded

    def test_path_d_overloaded(self) -> None:
        # PATH D is also a heavy path
        events = [_FakeEvent("D"), _FakeEvent("D"), _FakeEvent("D"), _FakeEvent("A")]
        dist = SessionDriftScorer.from_events(events)
        assert dist.is_overloaded
        assert dist.dominant_path == "D"

    def test_events_without_path_id_ignored(self) -> None:
        events = [_FakeEvent(""), _FakeEvent("A"), _FakeEvent("B")]
        dist = SessionDriftScorer.from_events(events)
        assert dist.total == 2
        assert "" not in dist.counts

    def test_overload_reason_contains_path_id(self) -> None:
        events = [_FakeEvent("C")] * 3 + [_FakeEvent("A")]
        dist = SessionDriftScorer.from_events(events)
        assert "PATH C" in dist.reason

    def test_no_overload_reason_contains_dominant_path(self) -> None:
        events = [_FakeEvent("A"), _FakeEvent("A"), _FakeEvent("B")]
        dist = SessionDriftScorer.from_events(events)
        assert "A" in dist.reason

    def test_from_jsonl_missing_file_no_overload(self) -> None:
        dist = SessionDriftScorer.from_jsonl(Path("/nonexistent/path.jsonl"))
        assert not dist.is_overloaded
        assert dist.total == 0

    def test_from_jsonl_parses_path_ids(self, tmp_path: Path) -> None:
        jsonl_file = tmp_path / "events.jsonl"
        lines = [
            json.dumps({"event": "governance.ask", "path_id": "A"}),
            json.dumps({"event": "governance.ask", "path_id": "C"}),
            json.dumps({"event": "governance.ask", "path_id": "C"}),
            json.dumps({"event": "governance.ask", "path_id": "C"}),
        ]
        jsonl_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        dist = SessionDriftScorer.from_jsonl(jsonl_file)
        assert dist.total == 4
        assert dist.counts["C"] == 3
        assert dist.is_overloaded

    def test_from_jsonl_skips_malformed_lines(self, tmp_path: Path) -> None:
        jsonl_file = tmp_path / "events.jsonl"
        jsonl_file.write_text(
            '{"path_id": "A"}\nNOT_JSON\n{"path_id": "B"}\n', encoding="utf-8"
        )
        dist = SessionDriftScorer.from_jsonl(jsonl_file)
        assert dist.total == 2

    def test_from_jsonl_skips_empty_path_id(self, tmp_path: Path) -> None:
        jsonl_file = tmp_path / "events.jsonl"
        lines = [
            json.dumps({"path_id": ""}),
            json.dumps({"path_id": "A"}),
            json.dumps({}),  # no path_id key
        ]
        jsonl_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        dist = SessionDriftScorer.from_jsonl(jsonl_file)
        assert dist.total == 1
        assert dist.counts["A"] == 1

    def test_heavy_path_at_exactly_50_pct_not_overloaded(self) -> None:
        """Boundary: heavy path at exactly 50% → NOT overloaded (threshold is strict >)."""
        # 2 out of 4 = 50.0% — must NOT trigger overload
        events = [_FakeEvent("C"), _FakeEvent("C"), _FakeEvent("A"), _FakeEvent("B")]
        dist = SessionDriftScorer.from_events(events)
        assert dist.dominant_path == "C"
        assert not dist.is_overloaded

    def test_heavy_path_just_above_50_pct_is_overloaded(self) -> None:
        """Boundary: heavy path at 60% (3/5 > 50%) → overloaded."""
        events = [
            _FakeEvent("C"),
            _FakeEvent("C"),
            _FakeEvent("C"),
            _FakeEvent("A"),
            _FakeEvent("B"),
        ]
        dist = SessionDriftScorer.from_events(events)
        assert dist.dominant_path == "C"
        assert dist.is_overloaded
