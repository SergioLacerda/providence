"""Tests for newly extracted compliance classes.

Covers:
- ComplianceModePolicy (mode resolution, event filtering)
- ComplianceRecordValidator (schema validation, redaction)
- ComplianceLogStore (I/O operations, rotation, ASK logging)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_core.governance.compliance_log_store import ComplianceLogStore
from providence_core.governance.compliance_mode_policy import ComplianceModePolicy
from providence_core.governance.compliance_record_validator import (
    ComplianceRecordValidator,
)

# ---------------------------------------------------------------------------
# ComplianceModePolicy Tests
# ---------------------------------------------------------------------------


class TestComplianceModePolicy:
    """Tests for ComplianceModePolicy mode resolution and filtering."""

    def test_resolve_logging_mode_env_var_takes_precedence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SDD_LOGGING_MODE env var overrides profile."""
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        assert ComplianceModePolicy.resolve_logging_mode(profile="client") == "active"

    def test_resolve_logging_mode_client_profile_defaults_passive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Client profile defaults to passive mode."""
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        assert ComplianceModePolicy.resolve_logging_mode(profile="client") == "passive"

    def test_resolve_logging_mode_master_profile_defaults_active(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Master profile defaults to active mode."""
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        assert ComplianceModePolicy.resolve_logging_mode(profile="master") == "active"

    def test_resolve_logging_mode_empty_profile_defaults_passive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty/unknown profile defaults to passive."""
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        assert ComplianceModePolicy.resolve_logging_mode(profile="") == "passive"

    def test_should_persist_event_all_events_in_active_mode(self) -> None:
        """Active mode persists all events."""
        assert ComplianceModePolicy.should_persist_event("test.event", "active") is True
        assert (
            ComplianceModePolicy.should_persist_event("COMMAND_INVOKED", "active")
            is True
        )

    def test_should_persist_event_all_events_in_strict_mode(self) -> None:
        """Strict mode persists all events."""
        assert ComplianceModePolicy.should_persist_event("test.event", "strict") is True

    def test_should_persist_event_mandatory_in_passive_mode(self) -> None:
        """Passive mode only persists mandatory events."""
        assert ComplianceModePolicy.should_persist_event("violation", "passive") is True
        assert (
            ComplianceModePolicy.should_persist_event("workspace_init", "passive")
            is True
        )
        assert (
            ComplianceModePolicy.should_persist_event("compile_complete", "passive")
            is True
        )
        assert (
            ComplianceModePolicy.should_persist_event("governance_checked", "passive")
            is True
        )

    def test_should_persist_event_non_mandatory_filtered_in_passive(self) -> None:
        """Non-mandatory events filtered in passive mode."""
        assert (
            ComplianceModePolicy.should_persist_event("COMMAND_INVOKED", "passive")
            is False
        )
        assert (
            ComplianceModePolicy.should_persist_event("test.event", "passive") is False
        )

    def test_mandatory_events_case_insensitive(self) -> None:
        """Mandatory event check is case-insensitive."""
        assert ComplianceModePolicy.should_persist_event("VIOLATION", "passive") is True
        assert ComplianceModePolicy.should_persist_event("Violation", "passive") is True


# ---------------------------------------------------------------------------
# ComplianceRecordValidator Tests
# ---------------------------------------------------------------------------


class TestComplianceRecordValidator:
    """Tests for record validation and sensitive data redaction."""

    def test_validate_record_valid_with_all_fields(self) -> None:
        """Valid record with all required fields passes."""
        record = {
            "timestamp": "2026-05-16T10:00:00Z",
            "event": "test.event",
            "command": "test",
            "profile": "client",
            "state": "ACTIVE",
            "details": {"key": "value"},
            "level": "info",
            "service": "sdd",
            "message": "Test message",
            "status": "ok",
        }
        valid, missing = ComplianceRecordValidator.validate_record(record)
        assert valid is True
        assert missing == []

    def test_validate_record_missing_field(self) -> None:
        """Record missing required field fails."""
        record = {
            "timestamp": "2026-05-16T10:00:00Z",
            "event": "test.event",
            "command": "test",
            "profile": "client",
            "state": "ACTIVE",
            # details missing
            "level": "info",
            "service": "sdd",
            "message": "Test",
            "status": "ok",
        }
        valid, missing = ComplianceRecordValidator.validate_record(record)
        assert valid is False
        assert "details" in missing

    def test_validate_record_non_dict_input(self) -> None:
        """Non-dict input fails validation."""
        valid, missing = ComplianceRecordValidator.validate_record("not a dict")
        assert valid is False
        assert len(missing) > 0

    def test_redact_sensitive_query_key(self) -> None:
        """Query field is redacted."""
        details = {"query": "my secret query", "context": "public"}
        redacted = ComplianceRecordValidator.redact_sensitive(details)
        assert redacted["query"] == "[REDACTED]"
        assert redacted["context"] == "public"

    def test_redact_sensitive_multiple_keys(self) -> None:
        """Multiple sensitive keys are redacted."""
        details = {
            "query": "secret",
            "token": "abc123",
            "api_key": "key-secret",
            "password": "pass123",
            "context": "public",
        }
        redacted = ComplianceRecordValidator.redact_sensitive(details)
        assert redacted["query"] == "[REDACTED]"
        assert redacted["token"] == "[REDACTED]"
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["password"] == "[REDACTED]"
        assert redacted["context"] == "public"

    def test_redact_sensitive_preserves_original(self) -> None:
        """Original dict not mutated by redaction."""
        original = {"query": "sensitive", "safe": "data"}
        ComplianceRecordValidator.redact_sensitive(original)
        assert original["query"] == "sensitive"

    def test_redact_sensitive_none_input(self) -> None:
        """None input returns None."""
        assert ComplianceRecordValidator.redact_sensitive(None) is None

    def test_redact_sensitive_empty_dict(self) -> None:
        """Empty dict handled correctly."""
        result = ComplianceRecordValidator.redact_sensitive({})
        assert result == {}


# ---------------------------------------------------------------------------
# ComplianceLogStore Tests
# ---------------------------------------------------------------------------


class TestComplianceLogStore:
    """Tests for log store I/O operations."""

    def test_resolve_env_ci_detected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CI environment detected from CI env var."""
        monkeypatch.setenv("CI", "1")
        assert ComplianceLogStore._resolve_env() == "ci"

    def test_resolve_env_sdd_env_prod(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SDD_ENV=prod is recognized."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setenv("SDD_ENV", "prod")
        assert ComplianceLogStore._resolve_env() == "prod"

    def test_resolve_env_defaults_to_dev(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unknown environment defaults to dev."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SDD_ENV", raising=False)
        assert ComplianceLogStore._resolve_env() == "dev"

    def test_append_writes_valid_jsonl(self, tmp_path: Path) -> None:
        """Append writes valid JSONL line."""
        log_path = tmp_path / "events.jsonl"
        ComplianceLogStore.append(
            "test.event",
            command="test",
            profile="master",
            state="ACTIVE",
            details={"key": "value"},
            log_path=log_path,
        )
        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["event"] == "test.event"
        assert record["command"] == "test"

    def test_append_respects_passive_mode(self, tmp_path: Path) -> None:
        """Append respects passive mode filtering."""
        log_path = tmp_path / "events.jsonl"
        # Non-mandatory event in passive mode should not be written
        ComplianceLogStore.append(
            "non_mandatory_event",
            command="test",
            profile="client",
            state="ACTIVE",
            details={},
            log_path=log_path,
        )
        assert not log_path.exists()

    def test_append_writes_mandatory_in_passive(self, tmp_path: Path) -> None:
        """Mandatory events written even in passive mode."""
        log_path = tmp_path / "events.jsonl"
        ComplianceLogStore.append(
            "violation",
            command="test",
            profile="client",
            state="ACTIVE",
            details={},
            log_path=log_path,
        )
        assert log_path.exists()

    def test_read_returns_last_n_events(self, tmp_path: Path) -> None:
        """Read returns last N events."""
        log_path = tmp_path / "events.jsonl"
        # Write 5 events
        for i in range(5):
            ComplianceLogStore.append(
                "test.event",
                command="test",
                profile="master",
                state="ACTIVE",
                details={"index": i},
                log_path=log_path,
            )
        events = ComplianceLogStore.read(n=3, log_path=log_path)
        assert len(events) == 3
        assert events[-1]["details"]["index"] == 4

    def test_read_returns_all_events_when_n_zero(self, tmp_path: Path) -> None:
        """Read with n=0 returns all events."""
        log_path = tmp_path / "events.jsonl"
        for i in range(5):
            ComplianceLogStore.append(
                "test.event",
                command="test",
                profile="master",
                state="ACTIVE",
                details={"index": i},
                log_path=log_path,
            )
        events = ComplianceLogStore.read(n=0, log_path=log_path)
        assert len(events) == 5

    def test_read_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Read on missing file returns empty list."""
        log_path = tmp_path / "nonexistent.jsonl"
        events = ComplianceLogStore.read(log_path=log_path)
        assert events == []

    def test_read_skips_malformed_lines(self, tmp_path: Path) -> None:
        """Read tolerates and skips malformed JSON lines."""
        log_path = tmp_path / "events.jsonl"
        # Write valid line
        log_path.write_text(
            '{"event": "valid"}\nthis is not json\n{"event": "also_valid"}\n',
            encoding="utf-8",
        )
        events = ComplianceLogStore.read(log_path=log_path)
        assert len(events) == 2
        assert events[0]["event"] == "valid"

    def test_log_ask_includes_agent_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Log_ask propagates agent_id as a top-level record field."""
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log_path = tmp_path / "events.jsonl"
        ComplianceLogStore.log_ask(
            event="ask_command",
            command="ask",
            profile="client",
            state="ACTIVE",
            agent_id="agent-123",
            details={"query": "test"},
            log_path=log_path,
        )
        events = ComplianceLogStore.read(log_path=log_path)
        assert len(events) == 1
        assert events[0]["agent_id"] == "agent-123"

    def test_append_propagates_agent_id(self, tmp_path: Path) -> None:
        """Append writes agent_id as a top-level record field."""
        log_path = tmp_path / "events.jsonl"
        ComplianceLogStore.append(
            "violation",
            command="test",
            profile="master",
            state="ACTIVE",
            agent_id="cli-agent",
            details={},
            log_path=log_path,
        )
        events = ComplianceLogStore.read(log_path=log_path)
        assert len(events) == 1
        assert events[0]["agent_id"] == "cli-agent"

    def test_append_resolves_agent_id_from_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Append resolves agent_id from SDD_AGENT_ID when param is empty."""
        monkeypatch.setenv("SDD_AGENT_ID", "env-agent")
        log_path = tmp_path / "events.jsonl"
        ComplianceLogStore.append(
            "violation",
            command="test",
            profile="master",
            state="ACTIVE",
            details={},
            log_path=log_path,
        )
        events = ComplianceLogStore.read(log_path=log_path)
        assert len(events) == 1
        assert events[0]["agent_id"] == "env-agent"

    def test_log_ask_respects_passive_mode(self, tmp_path: Path) -> None:
        """Log_ask respects passive mode for ask_command."""
        log_path = tmp_path / "events.jsonl"
        # ask_command is not in mandatory events, so it should be filtered in passive
        ComplianceLogStore.log_ask(
            event="ask_command",
            command="ask",
            profile="client",
            state="ACTIVE",
            agent_id="agent-123",
            details={},
            log_path=log_path,
        )
        assert not log_path.exists()

    def test_rotate_skips_small_files(self, tmp_path: Path) -> None:
        """Rotate returns False for files smaller than threshold."""
        log_path = tmp_path / "events.jsonl"
        log_path.write_text("small content", encoding="utf-8")
        result = ComplianceLogStore.rotate(log_path, max_bytes=1000, max_backups=3)
        assert result is False
        assert log_path.exists()

    def test_rotate_creates_backup_chain(self, tmp_path: Path) -> None:
        """Rotate creates proper backup chain."""
        log_path = tmp_path / "events.jsonl"
        # Create large file
        log_path.write_text("x" * 11 * 1024 * 1024, encoding="utf-8")
        result = ComplianceLogStore.rotate(
            log_path, max_bytes=10 * 1024 * 1024, max_backups=3
        )
        assert result is True
        assert log_path.exists()  # New empty log created
        assert (tmp_path / "events.jsonl.1").exists()  # Backup created


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
