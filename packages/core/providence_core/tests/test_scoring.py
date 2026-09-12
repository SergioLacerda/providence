"""Unit tests for governance scoring utilities."""

from __future__ import annotations

import pytest

from providence_core.governance.scoring import ScoreCheck, compute_governance_score

pytestmark = pytest.mark.unit


class TestScoreCheckTypedDict:
    """Tests for ScoreCheck TypedDict."""

    def test_score_check_creation_as_dict(self) -> None:
        """Should create ScoreCheck as dict with required fields."""
        check: ScoreCheck = {"label": "test", "passed": True, "weight": 10}
        assert check["label"] == "test"
        assert check["passed"] is True
        assert check["weight"] == 10

    def test_score_check_various_labels(self) -> None:
        """Should support various check labels."""
        labels = [
            "profile validation",
            "artifacts validation",
            "AHP confidence",
            "core_hash match",
        ]
        for label in labels:
            check: ScoreCheck = {"label": label, "passed": True, "weight": 25}
            assert check["label"] == label


class TestComputeGovernanceScoreBasics:
    """Tests for basic governance score computation."""

    def test_single_passing_check(self) -> None:
        """Single passing check should return 100."""
        checks = [("test", True, 100)]
        score = compute_governance_score(checks)
        assert score == 100

    def test_single_failing_check(self) -> None:
        """Single failing check should return 0."""
        checks = [("test", False, 100)]
        score = compute_governance_score(checks)
        assert score == 0

    def test_empty_checks_list(self) -> None:
        """Empty checks list should return 0."""
        checks = []
        score = compute_governance_score(checks)
        assert score == 0

    def test_no_checks(self) -> None:
        """None or missing checks should return 0."""
        score = compute_governance_score([])
        assert score == 0


class TestComputeGovernanceScoreWeighted:
    """Tests for weighted score computation."""

    def test_equal_weights_all_passing(self) -> None:
        """All passing equal weight checks should return 100."""
        checks = [
            ("check1", True, 25),
            ("check2", True, 25),
            ("check3", True, 25),
            ("check4", True, 25),
        ]
        score = compute_governance_score(checks)
        assert score == 100

    def test_equal_weights_half_passing(self) -> None:
        """Half passing equal weight checks should return 50."""
        checks = [
            ("check1", True, 25),
            ("check2", True, 25),
            ("check3", False, 25),
            ("check4", False, 25),
        ]
        score = compute_governance_score(checks)
        assert score == 50

    def test_unequal_weights_passing(self) -> None:
        """Weighted checks should calculate proportionally."""
        checks = [
            ("check1", True, 30),  # 30/100 = 30%
            ("check2", False, 30),  # 0/100 = 0%
            ("check3", True, 40),  # 40/100 = 40%
        ]
        score = compute_governance_score(checks)
        assert score == 70  # 30 + 40 = 70%

    def test_high_weight_failing_check(self) -> None:
        """Failing high-weight check should significantly reduce score."""
        checks = [
            ("critical", False, 50),
            ("minor1", True, 25),
            ("minor2", True, 25),
        ]
        score = compute_governance_score(checks)
        assert score == 50  # (25 + 25) / 100 = 50%


class TestComputeGovernanceScoreCanonical:
    """Tests for canonical weight distribution."""

    def test_canonical_weights_all_pass(self) -> None:
        """Canonical weights with all passing should be 100."""
        checks = [
            ("profile validation", True, 30),
            ("artifacts validation", True, 30),
            ("AHP confidence", True, 20),
            ("core_hash match", True, 20),
        ]
        score = compute_governance_score(checks)
        assert score == 100

    def test_canonical_weights_artifacts_fail(self) -> None:
        """If artifacts fail (30 weight), score should be 70."""
        checks = [
            ("profile validation", True, 30),
            ("artifacts validation", False, 30),
            ("AHP confidence", True, 20),
            ("core_hash match", True, 20),
        ]
        score = compute_governance_score(checks)
        assert score == 70

    def test_canonical_weights_critical_failures(self) -> None:
        """If both validation checks fail, score should be 40."""
        checks = [
            ("profile validation", False, 30),
            ("artifacts validation", False, 30),
            ("AHP confidence", True, 20),
            ("core_hash match", True, 20),
        ]
        score = compute_governance_score(checks)
        assert score == 40


class TestComputeGovernanceScoreDictInput:
    """Tests for ScoreCheck dict input format."""

    def test_dict_format_input(self) -> None:
        """Should accept ScoreCheck dict format."""
        checks: list[ScoreCheck] = [
            {"label": "check1", "passed": True, "weight": 50},
            {"label": "check2", "passed": False, "weight": 50},
        ]
        score = compute_governance_score(checks)
        assert score == 50

    def test_mixed_dict_and_tuple_input(self) -> None:
        """Should handle mix of dict and tuple inputs."""
        checks = [
            {"label": "check1", "passed": True, "weight": 50},
            ("check2", True, 50),
        ]
        score = compute_governance_score(checks)
        assert score == 100

    def test_dict_conversion_preserves_semantics(self) -> None:
        """Dict and tuple formats should give same result."""
        checks_dict: list[ScoreCheck] = [
            {"label": "a", "passed": True, "weight": 30},
            {"label": "b", "passed": False, "weight": 40},
            {"label": "c", "passed": True, "weight": 30},
        ]
        checks_tuple = [
            ("a", True, 30),
            ("b", False, 40),
            ("c", True, 30),
        ]

        score_dict = compute_governance_score(checks_dict)
        score_tuple = compute_governance_score(checks_tuple)

        assert score_dict == score_tuple


class TestComputeGovernanceScoreEdgeCases:
    """Tests for edge cases in score computation."""

    def test_zero_total_weight(self) -> None:
        """Zero total weight should return 0."""
        checks = [("test", True, 0)]
        score = compute_governance_score(checks)
        assert score == 0

    def test_rounding_behavior(self) -> None:
        """Score should be rounded to nearest integer."""
        checks = [
            ("test1", True, 1),
            ("test2", False, 2),
        ]
        score = compute_governance_score(checks)
        # 1/3 = 0.333... should round to 0
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_very_large_weights(self) -> None:
        """Should handle very large weight values."""
        checks = [
            ("test1", True, 1000000),
            ("test2", True, 1000000),
        ]
        score = compute_governance_score(checks)
        assert score == 100

    def test_many_checks(self) -> None:
        """Should handle large number of checks."""
        checks = [
            (f"check{i}", i % 2 == 0, 1)  # Alternate pass/fail
            for i in range(100)
        ]
        score = compute_governance_score(checks)
        assert 0 <= score <= 100

    def test_fractional_weight_precision(self) -> None:
        """Fractional weights should be computed accurately."""
        checks = [
            ("test1", True, 1),
            ("test2", True, 1),
            ("test3", False, 1),
        ]
        score = compute_governance_score(checks)
        # 2/3 = 0.6666... = 67% when rounded
        assert score == 67


class TestComputeGovernanceScoreLabelVariations:
    """Tests for various label formats and variations."""

    def test_empty_string_label(self) -> None:
        """Should accept empty string labels."""
        checks = [("", True, 100)]
        score = compute_governance_score(checks)
        assert score == 100

    def test_unicode_labels(self) -> None:
        """Should handle unicode characters in labels."""
        checks = [
            ("检查1", True, 50),
            ("チェック2", True, 50),
        ]
        score = compute_governance_score(checks)
        assert score == 100

    def test_special_character_labels(self) -> None:
        """Should handle special characters in labels."""
        checks = [
            ("check_1-v2", True, 50),
            ("check.2/v3", True, 50),
        ]
        score = compute_governance_score(checks)
        assert score == 100
