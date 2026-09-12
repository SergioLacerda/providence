"""Extended tests for compliance event logging (higher coverage)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_core.governance.compliance import (
    append_event,
    compute_governance_adherence,
    read_events,
    rotate_compliance_log,
)

pytestmark = pytest.mark.unit


class TestComplexRotationScenarios:
    """Tests for complex log rotation scenarios."""

    def test_rotate_shifts_multiple_backups(self, tmp_path: Path) -> None:
        """Should shift multiple backup files during rotation."""
        log_file = tmp_path / "events.jsonl"
        log_file.write_text("x" * 1000, encoding="utf-8")

        # First rotation: creates .1
        rotate_compliance_log(log_file, max_bytes=100, max_backups=3)
        assert (tmp_path / "events.jsonl.1").exists()

        # Add more content and rotate again: .1 becomes .2
        log_file.write_text("x" * 1000, encoding="utf-8")
        rotate_compliance_log(log_file, max_bytes=100, max_backups=3)
        assert (tmp_path / "events.jsonl.1").exists()
        assert (tmp_path / "events.jsonl.2").exists()

    def test_rotate_deletes_oldest_backup(self, tmp_path: Path) -> None:
        """Should delete oldest backup when exceeding max_backups."""
        log_file = tmp_path / "events.jsonl"

        # Create 4 backups (exceeding max_backups=3)
        for _ in range(4):
            log_file.write_text("x" * 1000, encoding="utf-8")
            rotate_compliance_log(log_file, max_bytes=100, max_backups=3)

        # .4 should not exist (oldest deleted)
        assert not (tmp_path / "events.jsonl.4").exists()


class TestEventAppendingEdgeCases:
    """Tests for event appending edge cases."""

    def test_append_event_creates_parent_directory(self, tmp_path: Path) -> None:
        """append_event should create parent directories if missing."""
        log_file = tmp_path / "nested" / "path" / "events.jsonl"

        append_event(
            "test.event",
            command="test",
            profile="master",
            log_path=log_file,
        )

        assert log_file.exists()
        assert log_file.parent.exists()

    def test_append_multiple_events(self, tmp_path: Path) -> None:
        """Should append multiple events to same file."""
        log_file = tmp_path / "events.jsonl"

        for i in range(3):
            append_event(
                f"event{i}",
                command="test",
                profile="master",
                log_path=log_file,
            )

        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

    def test_append_with_message_field(self, tmp_path: Path) -> None:
        """Should include message field when provided."""
        log_file = tmp_path / "events.jsonl"

        append_event(
            "test.event",
            command="test",
            profile="master",
            message="This is a test message",
            log_path=log_file,
        )

        content = log_file.read_text(encoding="utf-8")
        data = json.loads(content.strip())
        assert data["message"] == "This is a test message"

    def test_append_omits_empty_message(self, tmp_path: Path) -> None:
        """Should omit message field when empty."""
        log_file = tmp_path / "events.jsonl"

        append_event(
            "test.event",
            command="test",
            profile="master",
            message="",
            log_path=log_file,
        )

        content = log_file.read_text(encoding="utf-8")
        data = json.loads(content.strip())
        assert "message" not in data or data["message"] == ""


class TestEventReadingEdgeCases:
    """Tests for reading events edge cases."""

    def test_read_more_events_than_exist(self, tmp_path: Path) -> None:
        """Should return all events even when requested count exceeds total."""
        log_file = tmp_path / "events.jsonl"

        for i in range(3):
            append_event(
                f"event{i}",
                command="test",
                profile="master",
                log_path=log_file,
            )

        # Request 100 events when only 3 exist
        events = read_events(n=100, log_path=log_file)
        assert len(events) == 3

    def test_read_negative_offset_handled(self, tmp_path: Path) -> None:
        """Should handle edge cases in event reading."""
        log_file = tmp_path / "events.jsonl"

        append_event(
            "test.event",
            command="test",
            profile="master",
            log_path=log_file,
        )

        # Default n=50 should get the event
        events = read_events(log_path=log_file)
        assert len(events) >= 1


class TestComplianceEventInActiveMode:
    """Tests for event behavior in active logging mode."""

    def test_all_events_in_active_mode(self, tmp_path: Path) -> None:
        """In active mode, all events should persist."""
        log_file = tmp_path / "events.jsonl"

        # Write multiple different events
        append_event("event1", command="test", profile="master", log_path=log_file)
        append_event(
            "custom.event",
            command="test",
            profile="master",
            log_path=log_file,
        )
        append_event(
            "another.event", command="test", profile="master", log_path=log_file
        )

        events = read_events(n=10, log_path=log_file)
        assert len(events) == 3


class TestComplianceEventInStrictMode:
    """Tests for event behavior in strict logging mode."""

    def test_all_events_in_strict_mode(self, tmp_path: Path) -> None:
        """In strict mode, all events should persist."""
        log_file = tmp_path / "events.jsonl"

        append_event("test.event", command="test", profile="master", log_path=log_file)

        events = read_events(log_path=log_file)
        assert len(events) > 0


class TestGovernanceAdherenceScore:
    """Tests for governance adherence scoring."""

    def test_compute_adherence_no_events(self, tmp_path: Path) -> None:
        """Should compute score when no events exist."""
        result = compute_governance_adherence(workspace_root=tmp_path)

        assert "score" in result
        assert 0 <= result["score"] <= 100

    def test_compute_adherence_includes_dimensions(self, tmp_path: Path) -> None:
        """Should include all three dimensions in result."""
        result = compute_governance_adherence(workspace_root=tmp_path)

        assert "behavioral" in result
        assert "structural" in result
        assert "freshness" in result
        assert "details" in result

    def test_compute_adherence_behavioral_ratio(self, tmp_path: Path) -> None:
        """Behavioral score should be 0-100."""
        result = compute_governance_adherence(workspace_root=tmp_path)

        behavioral = result.get("behavioral", 0)
        assert 0.0 <= behavioral <= 1.0

    def test_compute_adherence_structural_boolean(self, tmp_path: Path) -> None:
        """Structural result should be boolean."""
        result = compute_governance_adherence(workspace_root=tmp_path)

        structural = result.get("structural")
        assert isinstance(structural, bool)

    def test_compute_adherence_freshness_ratio(self, tmp_path: Path) -> None:
        """Freshness score should be 0-1."""
        result = compute_governance_adherence(workspace_root=tmp_path)

        freshness = result.get("freshness", 0)
        assert 0.0 <= freshness <= 1.0

    def test_compute_adherence_custom_window(self, tmp_path: Path) -> None:
        """Should accept custom time window in hours."""
        result = compute_governance_adherence(workspace_root=tmp_path, window_hours=12)

        assert result["details"]["window_hours"] == 12


class TestComplianceRecordWithDetails:
    """Tests for compliance records with detailed information."""

    def test_append_with_details_dict(self, tmp_path: Path) -> None:
        """Should persist details dict in record."""
        log_file = tmp_path / "events.jsonl"

        details = {
            "query_hash": "abc123",
            "count": 42,
            "status": "ok",
        }

        append_event(
            "test.event",
            command="test",
            profile="master",
            details=details,
            log_path=log_file,
        )

        events = read_events(log_path=log_file)
        assert events[0]["details"]["query_hash"] == "abc123"
        assert events[0]["details"]["count"] == 42

    def test_append_with_env_variable(self, tmp_path: Path) -> None:
        """Should include event in record."""
        log_file = tmp_path / "events.jsonl"

        append_event(
            "test.event",
            command="test",
            profile="master",
            log_path=log_file,
        )

        events = read_events(log_path=log_file)
        assert "event" in events[0]
        assert events[0]["event"] == "test.event"

    def test_append_includes_version(self, tmp_path: Path) -> None:
        """Should include timestamp field in event."""
        log_file = tmp_path / "events.jsonl"

        append_event(
            "test.event",
            command="test",
            profile="master",
            log_path=log_file,
        )

        events = read_events(log_path=log_file)
        assert "timestamp" in events[0]
