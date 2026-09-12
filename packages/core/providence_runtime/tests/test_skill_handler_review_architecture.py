from __future__ import annotations

from pathlib import Path

from providence_runtime._skill_executor import (
    ReviewArchitectureHandler,
    _build_architecture_review,
)


def test_build_architecture_review_reports_score_delta_and_added_violations() -> None:
    review = _build_architecture_review(
        {
            "governance_score": 72,
            "baseline_governance_score": 80,
            "architecture_violations": ["M001", "M010"],
            "baseline_architecture_violations": ["M001"],
        }
    )

    assert review["governance_score"] == 72
    assert review["architecture_deltas"]["score_delta"] == -8.0
    assert review["architecture_deltas"]["added_violations"] == ["M010"]
    assert (
        "run providence governance score --verbose and investigate score regression"
        in review["remediation_proposals"]
    )


def test_build_architecture_review_returns_stable_message_when_no_regression() -> None:
    review = _build_architecture_review(
        {
            "governance_score": 90,
            "baseline_governance_score": 90,
            "architecture_violations": [],
            "baseline_architecture_violations": [],
        }
    )

    assert review["architecture_deltas"]["score_delta"] == 0.0
    assert review["remediation_proposals"] == [
        "architecture review is stable; keep current mandate alignment"
    ]


def test_review_architecture_handler_returns_review_artifacts() -> None:
    handler = ReviewArchitectureHandler()
    outcome = handler.pre_run(
        {"governance_score": 88},
        learning=None,
        skill=None,
        profile="default",
        footer_fn=lambda d, g: "",
    )

    assert outcome.early_result is None
    assert outcome.artifacts["governance_score"] == 88
    assert "architecture_deltas" in outcome.artifacts


def test_review_architecture_handler_persists_baseline(tmp_path: Path) -> None:
    handler = ReviewArchitectureHandler()
    outcome = handler.pre_run(
        {
            "_project_root": str(tmp_path),
            "governance_score": 88,
            "architecture_violations": ["M010"],
        },
        learning=None,
        skill=None,
        profile="default",
        footer_fn=lambda d, g: "",
    )

    baseline_path = tmp_path / ".providence" / "runtime" / "architecture-baseline.json"
    assert baseline_path.exists()
    assert (
        outcome.artifacts["baseline_path"]
        == ".providence/runtime/architecture-baseline.json"
    )
    assert outcome.artifacts["baseline_updated"] is True
