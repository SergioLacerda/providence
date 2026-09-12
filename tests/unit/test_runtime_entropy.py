import json
from types import SimpleNamespace

from providence_runtime.entropy import (
    ConvergenceTracker,
    EntropyAdvisor,
    EntropyScore,
    PathDistribution,
    SessionDriftScorer,
)
from providence_runtime.entropy._convergence import _compute_trend


def test_entropy_score_compute():
    score = EntropyScore.compute(2, 3, 50.0, path_id="B")
    assert score.retry_count == 2
    assert score.reflection_count == 3
    assert score.budget_utilization_pct == 50.0
    assert score.path_id == "B"
    assert score.score == 3.0


def test_entropy_advisor_decompose():
    advisor = EntropyAdvisor()
    # Should decompose for PATH B (threshold 3.0)
    suggestion = advisor.advise(3, 3, 50.0, path_id="B")
    assert suggestion.should_decompose
    assert "exceeds threshold" in suggestion.reason
    # Should NOT decompose for PATH A (threshold 1.0)
    suggestion = advisor.advise(1, 1, 50.0, path_id="A")
    assert not suggestion.should_decompose
    assert "within threshold" in suggestion.reason


def test_entropy_advisor_default_threshold():
    advisor = EntropyAdvisor()
    # Unknown path uses default threshold (1.0)
    suggestion = advisor.advise(2, 1, 60.0, path_id="Z")
    assert suggestion.should_decompose
    assert suggestion.threshold == 1.0


def test_compute_trend_basic():
    # Increasing trend
    samples = [10, 20, 30]
    slope = _compute_trend(samples)
    assert slope > 0
    # Decreasing trend
    samples = [30, 20, 10]
    slope = _compute_trend(samples)
    assert slope < 0
    # Flat trend
    samples = [10, 10, 10]
    slope = _compute_trend(samples)
    assert slope == 0
    # Not enough samples
    assert _compute_trend([10]) == 0


def test_convergence_tracker_converging():
    tracker = ConvergenceTracker(window=3)
    tracker.record(30)
    tracker.record(25)
    tracker.record(20)
    report = tracker.report()
    assert report.is_converging
    assert "converging" in report.reason


def test_convergence_tracker_diverging():
    tracker = ConvergenceTracker(window=3)
    tracker.record(10)
    tracker.record(20)
    tracker.record(40)
    report = tracker.report()
    assert not report.is_converging
    assert "outpacing progress" in report.reason


def test_convergence_tracker_insufficient():
    tracker = ConvergenceTracker(window=3)
    tracker.record(10)
    report = tracker.report()
    assert report.is_converging
    assert "Insufficient samples" in report.reason


def test_path_distribution_repr():
    pd = PathDistribution(
        counts={"A": 2, "B": 3},
        total=5,
        dominant_path="B",
        is_overloaded=False,
        reason="Test reason",
    )
    assert "A" in repr(pd)
    assert "B" in repr(pd)


def test_session_drift_scorer_from_events():
    events = [SimpleNamespace(path_id="C") for _ in range(6)] + [
        SimpleNamespace(path_id="A") for _ in range(4)
    ]
    dist = SessionDriftScorer.from_events(events)
    assert dist.total == 10
    assert dist.dominant_path == "C"
    assert dist.is_overloaded
    assert "overloading" in dist.reason or "Systematic" in dist.reason
    # Within bounds
    events = [SimpleNamespace(path_id="A") for _ in range(10)]
    dist = SessionDriftScorer.from_events(events)
    assert not dist.is_overloaded
    assert "within bounds" in dist.reason


def test_session_drift_scorer_from_jsonl(tmp_path):
    jsonl = tmp_path / "drift.jsonl"
    data = [
        {"path_id": "C"},
        {"path_id": "C"},
        {"path_id": "C"},
        {"path_id": "A"},
        {"path_id": "A"},
    ]
    with open(jsonl, "w", encoding="utf-8") as f:
        for row in data:
            f.write(json.dumps(row) + "\n")
    dist = SessionDriftScorer.from_jsonl(jsonl)
    assert dist.total == 5
    assert dist.dominant_path == "C"
    assert dist.counts["C"] == 3
    assert dist.is_overloaded  # 3/5 = 60% > 50%
    # Empty file
    empty = tmp_path / "empty.jsonl"
    dist = SessionDriftScorer.from_jsonl(empty)
    assert dist.total == 0
    assert not dist.is_overloaded
    assert "No path_id" in dist.reason
