"""Extended test coverage for adherence_scorer.py edge cases."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from providence_core.governance.adherence_scorer import GovernanceAdherenceScorer


class TestComputeEdgeCases:
    """Test compute method edge cases when workspace resolution fails."""

    def test_compute_when_workspace_root_resolution_fails(self, tmp_path):
        """Verify compute handles workspace root resolution failure gracefully."""
        with patch(
            "providence_core.utils.environment.find_workspace_root",
            side_effect=RuntimeError("Not found"),
        ):
            result = GovernanceAdherenceScorer.compute()

        assert isinstance(result, dict)
        assert "score" in result
        # No events → behavioral = 1.0 * 50 = 50 pts, no state → structural/freshness = 0
        assert result["score"] == 50

    def test_compute_when_workspace_root_returns_none(self, tmp_path):
        """Verify compute handles None workspace root gracefully."""
        with patch(
            "providence_core.utils.environment.find_workspace_root", return_value=None
        ):
            result = GovernanceAdherenceScorer.compute()

        assert isinstance(result, dict)
        assert "score" in result
        # No events → behavioral = 1.0 * 50 = 50 pts, no state → structural/freshness = 0
        assert result["score"] == 50


class TestReadAllEvents:
    """Test compliance event reading with malformed data."""

    def test_read_events_skips_malformed_lines(self, tmp_path):
        """Verify _read_all_events skips malformed JSON lines."""
        log_file = tmp_path / "events.jsonl"
        log_file.write_text(
            '{"event": "valid"}\n'
            "{invalid json\n"
            '{"event": "also_valid"}\n'
            "not json at all\n",
            encoding="utf-8",
        )

        events = GovernanceAdherenceScorer._read_all_events(log_path=log_file)

        # Should only get the 2 valid lines
        assert len(events) == 2
        assert events[0]["event"] == "valid"
        assert events[1]["event"] == "also_valid"

    def test_read_events_returns_empty_on_read_error(self, tmp_path):
        """Verify _read_events returns [] when log file read fails."""
        log_file = tmp_path / "events.jsonl"
        log_file.write_text('{"event": "test"}', encoding="utf-8")

        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            events = GovernanceAdherenceScorer._read_all_events(log_path=log_file)

        assert events == []

    def test_read_events_handles_empty_file(self, tmp_path):
        """Verify _read_all_events handles empty JSONL file."""
        log_file = tmp_path / "events.jsonl"
        log_file.write_text("", encoding="utf-8")

        events = GovernanceAdherenceScorer._read_all_events(log_path=log_file)

        assert events == []


class TestGetCompiledFingerprint:
    """Test fingerprint extraction from compiled artifacts."""

    def test_fingerprint_returns_empty_when_root_resolution_fails(self):
        """Verify _get_compiled_fingerprint returns '' when workspace root resolution fails."""
        with patch(
            "providence_core.utils.environment.find_workspace_root",
            side_effect=RuntimeError("Not found"),
        ):
            fp = GovernanceAdherenceScorer._get_compiled_fingerprint()

        assert fp == ""

    def test_fingerprint_returns_empty_when_root_is_none(self):
        """Verify _get_compiled_fingerprint returns '' when workspace root is None."""
        with patch(
            "providence_core.utils.environment.find_workspace_root", return_value=None
        ):
            fp = GovernanceAdherenceScorer._get_compiled_fingerprint()

        assert fp == ""

    def test_fingerprint_computes_from_artifact_without_embedded_fp(self, tmp_path):
        """Verify _get_compiled_fingerprint computes SHA256 when artifact lacks fingerprint key."""
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)

        artifact_data = {
            "items": [{"id": "M001", "type": "MANDATE"}],
            # Note: no "fingerprint" key
        }
        artifact_file = compiled_dir / "governance-core.json"
        artifact_file.write_text(json.dumps(artifact_data), encoding="utf-8")

        fp = GovernanceAdherenceScorer._get_compiled_fingerprint(
            workspace_root=tmp_path
        )

        # Should compute SHA256 hash
        assert fp != ""
        assert len(fp) == 64  # SHA256 hex digest


class TestBehavioralScorer:
    """Test behavioral scoring with malformed timestamps."""

    def test_behavioral_skips_events_with_malformed_timestamps(self):
        """Verify _compute_behavioral skips events with malformed timestamps."""
        cutoff = datetime.now() - timedelta(hours=24)
        all_events = [
            {"ts": "", "event": "governance.checked"},  # empty
            {"ts": None, "event": "governance.checked"},  # null
            {"ts": "not-a-timestamp", "event": "governance.checked"},  # bad format
            {"event": "governance.checked"},  # missing ts
        ]

        result = GovernanceAdherenceScorer._compute_behavioral(all_events, cutoff)

        # All events should be skipped due to bad timestamps
        assert result["window_events"] == 0
        assert result["ratio"] == 1.0  # No events → perfect ratio

    def test_behavioral_handles_timezone_aware_timestamps(self):
        """Verify _compute_behavioral handles timezone-aware timestamps."""
        from providence_core.governance.compliance_constants import GOVERNANCE_CHECKED

        cutoff = datetime.now() - timedelta(hours=24)
        now = datetime.now()
        iso_with_tz = now.isoformat() + "+00:00"

        all_events = [
            {
                "ts": iso_with_tz,
                "event": GOVERNANCE_CHECKED,
            },
        ]

        result = GovernanceAdherenceScorer._compute_behavioral(all_events, cutoff)

        # Should process the event despite timezone
        assert result["window_events"] == 1
        assert result["allows"] == 1


class TestStructuralAndFreshness:
    """Test structural and freshness scoring edge cases."""

    def test_structural_no_artifact_detail(self, tmp_path):
        """Verify _compute_structural reports 'no_artifact' when artifact file missing."""
        state_file = tmp_path / "governance-state.json"
        state_file.write_text(
            json.dumps(
                {
                    "spec_fingerprint": "abc123def456",
                }
            ),
            encoding="utf-8",
        )

        # No artifact files exist
        result = GovernanceAdherenceScorer._compute_structural(
            resolved_state=state_file,
            workspace_root=tmp_path,
        )

        assert result["match"] is False
        assert result["detail"] == "no_artifact"
        assert result["score"] == 0

    def test_freshness_no_last_check_detail(self):
        """Verify _compute_freshness reports 'no_last_check' when timestamp missing."""
        state_data = {
            "spec_fingerprint": "abc123",
            # Note: no "last_check" key
        }
        now = datetime.now()

        result = GovernanceAdherenceScorer._compute_freshness(state_data, now)

        assert result["ratio"] == 0.0
        assert result["detail"] == "no_last_check"
        assert result["score"] == 0

    def test_freshness_decay_calculation(self):
        """Verify _compute_freshness calculates decay correctly."""
        now = datetime.now()
        # 15 minutes ago (within 30 minute client TTL)
        last_check = now - timedelta(minutes=15)

        state_data = {
            "spec_fingerprint": "abc123",
            "last_check": last_check.isoformat(),
            "profile": "client",  # 30 min TTL = 1800 seconds
        }

        result = GovernanceAdherenceScorer._compute_freshness(state_data, now)

        # 15 min elapsed / 30 min TTL = 0.5 ratio remaining
        assert 0.4 < result["ratio"] < 0.6
        assert result["score"] == 10  # 0.5 * 20 = 10
        assert "elapsed" in result["detail"]

    def test_behavioral_counts_violations(self):
        """Verify _compute_behavioral correctly counts violations."""
        from providence_core.governance.compliance_constants import (
            GOVERNANCE_CHECKED,
            VIOLATION,
        )

        cutoff = datetime.now() - timedelta(hours=24)
        now = datetime.now()

        all_events = [
            {"ts": now.isoformat(), "event": GOVERNANCE_CHECKED},
            {
                "ts": now.isoformat(),
                "event": VIOLATION,
                "details": {"action": "warn"},
            },
            {
                "ts": now.isoformat(),
                "event": VIOLATION,
                "details": {"action": "block"},
            },
        ]

        result = GovernanceAdherenceScorer._compute_behavioral(all_events, cutoff)

        assert result["allows"] == 1
        assert result["warns"] == 1
        assert result["blocks"] == 1
        # (1 allow) / (1 + 1 + 1) = 0.333...
        assert 0.3 < result["ratio"] < 0.35
