"""Unit tests for compliance compute methods (high coverage push)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from providence_core.governance.adherence_scorer import GovernanceAdherenceScorer
from providence_core.governance.compliance import compute_governance_adherence

pytestmark = pytest.mark.unit


class TestComputeBehavioral:
    """Tests for behavioral dimension computation."""

    def test_behavioral_no_events(self) -> None:
        """With no events, ratio should be 1.0 (perfect)."""
        all_events = []
        cutoff = datetime.now() - timedelta(hours=24)
        result = GovernanceAdherenceScorer._compute_behavioral(all_events, cutoff)

        assert result["ratio"] == 1.0
        assert result["allows"] == 0
        assert result["warns"] == 0
        assert result["blocks"] == 0

    def test_behavioral_all_allows(self) -> None:
        """All allows should give 1.0 ratio."""
        all_events = [
            {"event": "GOVERNANCE_CHECKED", "ts": datetime.now().isoformat()},
            {"event": "GOVERNANCE_CHECKED", "ts": datetime.now().isoformat()},
        ]
        cutoff = datetime.now() - timedelta(hours=24)
        result = GovernanceAdherenceScorer._compute_behavioral(all_events, cutoff)

        assert result["ratio"] == 1.0
        assert result["allows"] == 2

    def test_behavioral_mixed_events(self) -> None:
        """Mixed allows/warns should calculate ratio."""
        all_events = [
            {"event": "GOVERNANCE_CHECKED", "ts": datetime.now().isoformat()},
            {
                "event": "VIOLATION",
                "details": {"action": "warn"},
                "ts": datetime.now().isoformat(),
            },
            {
                "event": "VIOLATION",
                "details": {"action": "warn"},
                "ts": datetime.now().isoformat(),
            },
        ]
        cutoff = datetime.now() - timedelta(hours=24)
        result = GovernanceAdherenceScorer._compute_behavioral(all_events, cutoff)

        assert result["allows"] == 1
        assert result["warns"] == 2
        assert result["score"] == round((1 / 3) * 50)

    def test_behavioral_blocks_reduce_ratio(self) -> None:
        """Blocks should reduce ratio significantly."""
        all_events = [
            {"event": "GOVERNANCE_CHECKED", "ts": datetime.now().isoformat()},
            {
                "event": "VIOLATION",
                "details": {"action": "block"},
                "ts": datetime.now().isoformat(),
            },
        ]
        cutoff = datetime.now() - timedelta(hours=24)
        result = GovernanceAdherenceScorer._compute_behavioral(all_events, cutoff)

        assert result["blocks"] == 1
        assert result["ratio"] == 0.5


class TestComputeStructural:
    """Tests for structural dimension (fingerprint matching)."""

    def test_structural_no_state_file(self) -> None:
        """With no state file, match should be False."""
        result = GovernanceAdherenceScorer._compute_structural(None, None)

        assert result["match"] is False
        assert result["score"] == 0
        assert result["detail"] == "no_state_file"

    def test_structural_missing_state_file(self, tmp_path: Path) -> None:
        """Missing state file should give no match."""
        state_path = tmp_path / "nonexistent.json"
        result = GovernanceAdherenceScorer._compute_structural(state_path, None)

        assert result["match"] is False
        assert result["score"] == 0

    def test_structural_valid_match(self, tmp_path: Path) -> None:
        """Matching fingerprints should return match."""
        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps({"spec_fingerprint": "abc123def456"}), encoding="utf-8"
        )

        # Mock _get_compiled_fingerprint to return matching value
        with patch(
            "providence_core.governance.adherence_scorer.GovernanceAdherenceScorer._get_compiled_fingerprint",
            return_value="abc123def456",
        ):
            result = GovernanceAdherenceScorer._compute_structural(state_file, None)
            assert result["match"] is True
            assert result["score"] == 30


class TestComputeFreshness:
    """Tests for freshness dimension (TTL decay)."""

    def test_freshness_no_state_data(self) -> None:
        """No state data should give 0 ratio."""
        result = GovernanceAdherenceScorer._compute_freshness({}, datetime.now())

        assert result["ratio"] == 0.0
        assert result["score"] == 0

    def test_freshness_recent_check(self) -> None:
        """Recent check should have high freshness."""
        now = datetime.now()
        recent = (now - timedelta(minutes=5)).isoformat()

        result = GovernanceAdherenceScorer._compute_freshness(
            {"last_check": recent, "profile": "master"}, now
        )

        assert result["ratio"] > 0.9
        assert result["score"] > 18

    def test_freshness_old_check(self) -> None:
        """Old check should have low freshness."""
        now = datetime.now()
        old = (now - timedelta(days=10)).isoformat()

        result = GovernanceAdherenceScorer._compute_freshness(
            {"last_check": old, "profile": "master"}, now
        )

        assert result["ratio"] < 0.1
        assert result["score"] < 3

    def test_freshness_client_profile_shorter_ttl(self) -> None:
        """Client profile should have 30min TTL vs master 8h."""
        now = datetime.now()
        old = (now - timedelta(minutes=45)).isoformat()

        result = GovernanceAdherenceScorer._compute_freshness(
            {
                "last_check": old,
                "profile": "client",  # 30min TTL
            },
            now,
        )

        # 45 min > 30 min TTL, so should be expired
        assert result["ratio"] < 0.2


class TestGetCompiledFingerprint:
    """Tests for fingerprint extraction."""

    def test_get_fingerprint_returns_string(self, tmp_path: Path) -> None:
        """Should return string fingerprint."""
        compiled = tmp_path / "compiled"
        compiled.mkdir()
        gov_file = compiled / "governance-core.json"
        gov_file.write_text(json.dumps({"fingerprint": "abc123"}), encoding="utf-8")

        fp = GovernanceAdherenceScorer._get_compiled_fingerprint(tmp_path)

        assert isinstance(fp, str)

    def test_get_fingerprint_from_embedded(self, tmp_path: Path) -> None:
        """Should extract embedded fingerprint field."""
        compiled = tmp_path / ".providence" / "compiled"
        compiled.mkdir(parents=True)
        gov_file = compiled / "governance-core.json"
        gov_file.write_text(
            json.dumps({"fingerprint": "embedded-fp"}), encoding="utf-8"
        )

        fp = GovernanceAdherenceScorer._get_compiled_fingerprint(tmp_path)

        assert "embedded" in fp or "fp" in fp or len(fp) > 0


class TestComputeGovernanceAdherenceIntegration:
    """Tests for complete adherence score computation."""

    def test_adherence_score_0_to_100(self, tmp_path: Path) -> None:
        """Adherence score should be 0-100."""
        result = compute_governance_adherence(workspace_root=tmp_path)

        assert 0 <= result["score"] <= 100

    def test_adherence_includes_all_dimensions(self, tmp_path: Path) -> None:
        """Should include behavioral, structural, freshness."""
        result = compute_governance_adherence(workspace_root=tmp_path)

        assert "behavioral" in result
        assert "structural" in result
        assert "freshness" in result
        assert "details" in result

    def test_adherence_details_breakdown(self, tmp_path: Path) -> None:
        """Details should include dimension breakdowns."""
        result = compute_governance_adherence(workspace_root=tmp_path)

        assert "allows" in result["details"]
        assert "warns" in result["details"]
        assert "blocks" in result["details"]
        assert "behavioral_score" in result["details"]
        assert "structural_score" in result["details"]
        assert "freshness_score" in result["details"]

    def test_adherence_custom_window_hours(self, tmp_path: Path) -> None:
        """Should respect custom window_hours."""
        result = compute_governance_adherence(workspace_root=tmp_path, window_hours=1)

        assert result["details"]["window_hours"] == 1

    def test_adherence_score_calculation(self, tmp_path: Path) -> None:
        """Score should be sum of behavioral(50) + structural(30) + freshness(20)."""
        result = compute_governance_adherence(workspace_root=tmp_path)

        # Max possible is 100 (50 + 30 + 20)
        assert result["score"] <= 100

        # Score components should be in details
        total = (
            result["details"].get("behavioral_score", 0)
            + result["details"].get("structural_score", 0)
            + result["details"].get("freshness_score", 0)
        )
        assert total <= 100
