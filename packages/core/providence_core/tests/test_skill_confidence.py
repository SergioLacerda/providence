"""Tests for skill confidence scoring functions."""

from __future__ import annotations

import pytest

from providence_core.skill_confidence import (
    CONSERVATIVE_THRESHOLD,
    DEFAULT_WEIGHTS,
    EXECUTE_THRESHOLD,
    INTAKE_THRESHOLD,
    ConfidenceScores,
    compute_overall_confidence,
    interpret_confidence,
)

_FULL_SCORES = {
    "intent": 0.9,
    "route": 0.9,
    "scope": 0.9,
    "risk": 0.9,
    "validation": 0.9,
}


class TestConfidenceScores:
    def test_as_dict_contains_all_dimensions(self) -> None:
        cs = ConfidenceScores(
            intent=0.8, route=0.7, scope=0.6, risk=0.5, validation=0.4, overall=0.65
        )
        d = cs.as_dict()
        assert set(d.keys()) == {
            "intent",
            "route",
            "scope",
            "risk",
            "validation",
            "overall",
        }

    def test_as_dict_values_match(self) -> None:
        cs = ConfidenceScores(
            intent=0.8, route=0.7, scope=0.6, risk=0.5, validation=0.4, overall=0.65
        )
        assert cs.as_dict()["intent"] == 0.8
        assert cs.as_dict()["overall"] == 0.65

    def test_frozen_dataclass_immutable(self) -> None:
        cs = ConfidenceScores(
            intent=0.9, route=0.9, scope=0.9, risk=0.9, validation=0.9, overall=0.9
        )
        with pytest.raises((AttributeError, TypeError)):
            cs.intent = 0.1  # type: ignore[misc]


class TestComputeOverallConfidence:
    def test_valid_scores_returns_confidence_scores(self) -> None:
        result = compute_overall_confidence(_FULL_SCORES)
        assert isinstance(result, ConfidenceScores)
        assert 0.0 <= result.overall <= 1.0

    def test_weighted_average_is_correct(self) -> None:
        scores = {dim: 1.0 for dim in DEFAULT_WEIGHTS}
        result = compute_overall_confidence(scores)
        assert result.overall == 1.0

    def test_zero_scores_return_zero_overall(self) -> None:
        scores = {dim: 0.0 for dim in DEFAULT_WEIGHTS}
        result = compute_overall_confidence(scores)
        assert result.overall == 0.0

    def test_custom_weights_applied(self) -> None:
        scores = {dim: 0.0 for dim in DEFAULT_WEIGHTS}
        scores["intent"] = 1.0
        weights = {dim: 0.0 for dim in DEFAULT_WEIGHTS}
        weights["intent"] = 1.0
        result = compute_overall_confidence(scores, weights=weights)
        assert result.overall == 1.0

    def test_missing_dimension_raises_value_error(self) -> None:
        partial = {k: 0.5 for k in DEFAULT_WEIGHTS if k != "intent"}
        with pytest.raises(ValueError, match="Missing confidence dimensions"):
            compute_overall_confidence(partial)

    def test_unknown_dimension_raises_value_error(self) -> None:
        scores = {**_FULL_SCORES, "unknown_dim": 0.5}
        with pytest.raises(ValueError, match="Unknown confidence dimensions"):
            compute_overall_confidence(scores)

    def test_value_above_1_raises(self) -> None:
        scores = {**_FULL_SCORES, "intent": 1.1}
        with pytest.raises(ValueError, match="must be in \\[0.0, 1.0\\]"):
            compute_overall_confidence(scores)

    def test_value_below_0_raises(self) -> None:
        scores = {**_FULL_SCORES, "route": -0.1}
        with pytest.raises(ValueError, match="must be in \\[0.0, 1.0\\]"):
            compute_overall_confidence(scores)

    def test_overall_rounded_to_4_decimals(self) -> None:
        scores = {dim: 1.0 / 3.0 for dim in DEFAULT_WEIGHTS}
        result = compute_overall_confidence(scores)
        # overall should be rounded to at most 4 decimal places
        assert result.overall == round(result.overall, 4)

    def test_individual_dimensions_stored(self) -> None:
        result = compute_overall_confidence(_FULL_SCORES)
        assert result.intent == 0.9
        assert result.route == 0.9
        assert result.scope == 0.9
        assert result.risk == 0.9
        assert result.validation == 0.9


class TestInterpretConfidence:
    def test_execute_at_threshold(self) -> None:
        assert interpret_confidence(EXECUTE_THRESHOLD) == "execute"

    def test_execute_above_threshold(self) -> None:
        assert interpret_confidence(1.0) == "execute"

    def test_conservative_just_below_execute(self) -> None:
        assert interpret_confidence(EXECUTE_THRESHOLD - 0.01) == "conservative"

    def test_conservative_at_threshold(self) -> None:
        assert interpret_confidence(CONSERVATIVE_THRESHOLD) == "conservative"

    def test_intake_just_below_conservative(self) -> None:
        assert interpret_confidence(CONSERVATIVE_THRESHOLD - 0.01) == "intake"

    def test_intake_at_threshold(self) -> None:
        assert interpret_confidence(INTAKE_THRESHOLD) == "intake"

    def test_degraded_below_intake(self) -> None:
        assert interpret_confidence(INTAKE_THRESHOLD - 0.01) == "degraded"

    def test_degraded_at_zero(self) -> None:
        assert interpret_confidence(0.0) == "degraded"
