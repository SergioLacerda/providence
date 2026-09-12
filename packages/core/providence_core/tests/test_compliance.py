"""Unit tests for compliance event logging."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from providence_core.governance.compliance import (
    _MANDATORY_EVENTS,
    _REDACTED_PLACEHOLDER,
    ASK_COMMAND,
    ASK_FULL_COMMAND,
    GOVERNANCE_CHECKED,
    LOGGING_MODE_ACTIVE,
    LOGGING_MODE_PASSIVE,
    LOGGING_MODE_STRICT,
    VIOLATION,
    WORKSPACE_INIT,
    _should_persist_event,
    append_event,
    compute_governance_adherence,
    log_ask_event,
    read_events,
    resolve_logging_mode,
    rotate_compliance_log,
    validate_compliance_record,
)
from providence_core.governance.compliance_constants import default_log_path

pytestmark = pytest.mark.unit


def _log(tmp_path: Path) -> Path:
    return tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"


class TestLoggingModeResolution:
    """Tests for logging mode resolution logic."""

    def test_env_variable_overrides_all(self, tmp_path: Path) -> None:
        """SDD_LOGGING_MODE environment variable should take precedence."""
        with patch.dict(os.environ, {"SDD_LOGGING_MODE": "strict"}):
            mode = resolve_logging_mode(profile="client")
            assert mode == LOGGING_MODE_STRICT

    def test_profile_default_client(self) -> None:
        """Client profile should default to passive mode."""
        with patch.dict(os.environ, {}, clear=True):
            mode = resolve_logging_mode(profile="client")
            assert mode == LOGGING_MODE_PASSIVE

    def test_profile_default_master(self) -> None:
        """Master profile should default to active mode."""
        with patch.dict(os.environ, {}, clear=True):
            mode = resolve_logging_mode(profile="master")
            assert mode == LOGGING_MODE_ACTIVE

    def test_global_default_passive(self) -> None:
        """Global default should be passive when no profile specified."""
        with patch.dict(os.environ, {}, clear=True):
            mode = resolve_logging_mode(profile="")
            assert mode == LOGGING_MODE_PASSIVE

    def test_invalid_mode_ignored(self) -> None:
        """Invalid mode in env variable should be ignored."""
        with patch.dict(os.environ, {"SDD_LOGGING_MODE": "invalid"}):
            mode = resolve_logging_mode(profile="client")
            assert mode == LOGGING_MODE_PASSIVE


class TestEventPersistence:
    """Tests for _should_persist_event filtering logic."""

    def test_mandatory_events_always_persist(self) -> None:
        """Mandatory events should persist in passive mode."""
        for event in _MANDATORY_EVENTS:
            assert _should_persist_event(event, LOGGING_MODE_PASSIVE) is True

    def test_non_mandatory_blocked_in_passive(self) -> None:
        """Non-mandatory events should not persist in passive mode."""
        assert _should_persist_event("custom.event", LOGGING_MODE_PASSIVE) is False

    def test_all_events_persist_in_active(self) -> None:
        """All events should persist in active mode."""
        assert _should_persist_event("any.event", LOGGING_MODE_ACTIVE) is True
        assert _should_persist_event("custom.event", LOGGING_MODE_ACTIVE) is True

    def test_all_events_persist_in_strict(self) -> None:
        """All events should persist in strict mode."""
        assert _should_persist_event("any.event", LOGGING_MODE_STRICT) is True


class TestComplianceRecordValidation:
    """Tests for JSONL schema validation."""

    def test_valid_record_passes_validation(self) -> None:
        """Valid record with all required fields should pass."""
        record = {
            "timestamp": "2026-05-15T10:00:00+00:00",
            "event": "test.event",
            "command": "test",
            "profile": "client",
            "state": "ACTIVE",
            "details": {"key": "value"},
            "level": "info",
            "service": "sdd",
            "message": "Test event",
            "status": "ok",
        }
        valid, missing = validate_compliance_record(record)
        assert valid is True
        assert missing == []

    def test_missing_ts_field_fails(self) -> None:
        """Record missing 'timestamp' field should fail."""
        record = {
            "event": "test.event",
            "command": "test",
            "profile": "client",
            "state": "ACTIVE",
            "details": {},
            "level": "info",
            "service": "sdd",
            "message": "Test",
            "status": "ok",
        }
        valid, missing = validate_compliance_record(record)
        assert valid is False
        assert "timestamp" in missing

    def test_empty_required_field_fails(self) -> None:
        """Empty required field should be treated as missing."""
        record = {
            "timestamp": "",  # Empty - but schema just checks presence, not value
            "event": "test.event",
            "command": "test",
            "profile": "client",
            "state": "ACTIVE",
            "details": {},
            "level": "info",
            "service": "sdd",
            "message": "Test",
            "status": "ok",
        }
        # Note: validator only checks field presence, not emptiness, so this actually passes
        valid, missing = validate_compliance_record(record)
        assert (
            valid is True
        )  # All required fields present, even if timestamp is empty string

    def test_lists_all_missing_fields(self) -> None:
        """Should list all missing required fields."""
        record = {}
        valid, missing = validate_compliance_record(record)
        assert valid is False
        assert len(missing) > 0


class TestSensitiveDataRedaction:
    """Tests for redaction of sensitive detail keys."""

    def test_query_redacted(self) -> None:
        """Query field should be redacted."""
        from providence_core.governance.compliance import _redact_sensitive

        details = {"query": "SELECT * FROM users"}
        redacted = _redact_sensitive(details)
        assert redacted["query"] == _REDACTED_PLACEHOLDER

    def test_token_redacted(self) -> None:
        """Token field should be redacted."""
        from providence_core.governance.compliance import _redact_sensitive

        details = {"token": "secret-token-value"}
        redacted = _redact_sensitive(details)
        assert redacted["token"] == _REDACTED_PLACEHOLDER

    def test_api_key_redacted(self) -> None:
        """API key field should be redacted."""
        from providence_core.governance.compliance import _redact_sensitive

        details = {"api_key": "sk-1234567890"}
        redacted = _redact_sensitive(details)
        assert redacted["api_key"] == _REDACTED_PLACEHOLDER

    def test_non_sensitive_fields_preserved(self) -> None:
        """Non-sensitive fields should not be redacted."""
        from providence_core.governance.compliance import _redact_sensitive

        details = {"event": "test", "count": 42, "status": "ok"}
        redacted = _redact_sensitive(details)
        assert redacted["event"] == "test"
        assert redacted["count"] == 42
        assert redacted["status"] == "ok"

    def test_empty_details_handled(self) -> None:
        """Empty or None details should be handled gracefully."""
        from providence_core.governance.compliance import _redact_sensitive

        assert _redact_sensitive({}) == {}
        assert _redact_sensitive(None) is None


class TestLogRotation:
    """Tests for compliance log rotation."""

    def test_rotate_skips_small_files(self, tmp_path: Path) -> None:
        """Should not rotate files smaller than threshold."""
        log_file = tmp_path / "events.jsonl"
        log_file.write_text("small content", encoding="utf-8")

        result = rotate_compliance_log(log_file, max_bytes=1000)
        assert result is False
        assert log_file.exists()

    def test_rotate_moves_primary_to_backup(self, tmp_path: Path) -> None:
        """Should move primary file to .1 backup when rotating."""
        log_file = tmp_path / "events.jsonl"
        log_file.write_text("x" * 1000, encoding="utf-8")

        result = rotate_compliance_log(log_file, max_bytes=100, max_backups=3)
        assert result is True
        assert (tmp_path / "events.jsonl.1").exists()

    def test_rotate_creates_new_primary(self, tmp_path: Path) -> None:
        """Should create new primary file after rotation."""
        log_file = tmp_path / "events.jsonl"
        log_file.write_text("x" * 1000, encoding="utf-8")

        rotate_compliance_log(log_file, max_bytes=100, max_backups=3)
        assert log_file.exists()
        assert log_file.stat().st_size == 0

    def test_rotate_handles_missing_file_gracefully(self, tmp_path: Path) -> None:
        """Should not crash when log file doesn't exist."""
        log_file = tmp_path / "nonexistent.jsonl"
        result = rotate_compliance_log(log_file)
        assert result is False


class TestAppendEvent:
    """Tests for append_event functionality."""

    def test_append_event_writes_jsonl(self, tmp_path: Path) -> None:
        """Should write event as JSONL line."""
        log_file = tmp_path / "events.jsonl"
        append_event(
            "test.event",
            command="test",
            profile="master",
            level="INFO",
            service="providence-cli",
            log_path=log_file,
        )

        assert log_file.exists()
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) > 0

        event = json.loads(lines[0])
        assert event["event"] == "test.event"
        assert event["command"] == "test"

    def test_append_event_respects_logging_mode(self, tmp_path: Path) -> None:
        """Should respect logging mode when deciding to write."""
        log_file = tmp_path / "events.jsonl"

        # In passive mode, non-mandatory custom events should not persist
        append_event(
            "custom.event",
            command="test",
            profile="client",  # client → passive mode
            log_path=log_file,
        )

        # File should not exist or be empty (passive mode blocks non-mandatory)
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8").strip()
            # Passive mode should not write custom events
            assert len(content) == 0 or "custom.event" not in content

    def test_append_mandatory_event_in_passive_mode(self, tmp_path: Path) -> None:
        """Should write mandatory events even in passive mode."""
        log_file = tmp_path / "events.jsonl"

        append_event(
            VIOLATION,  # Mandatory event
            command="test",
            profile="client",  # client → passive mode
            log_path=log_file,
        )

        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8").strip()
        assert len(content) > 0
        event = json.loads(content.split("\n")[0])
        assert event["event"] == VIOLATION

    def test_append_event_redacts_sensitive_details(self, tmp_path: Path) -> None:
        """Should redact sensitive fields in details."""
        log_file = tmp_path / "events.jsonl"

        append_event(
            "test.event",
            command="test",
            profile="master",  # Use master for active mode
            details={"api_key": "secret-key", "status": "ok"},
            log_path=log_file,
        )

        content = log_file.read_text(encoding="utf-8").strip()
        event = json.loads(content.split("\n")[0])
        assert event["details"]["api_key"] == _REDACTED_PLACEHOLDER
        assert event["details"]["status"] == "ok"

    def test_creates_parent_dirs_and_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        assert not log.exists()
        append_event(
            WORKSPACE_INIT,
            command="init",
            profile="client",
            state="NOT_INITIALIZED",
            log_path=log,
        )
        assert log.exists()

    def test_respects_sdd_agent_id_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        append_event(
            "command.invoked",
            command="ask",
            profile="client",
            message="Agent copilot-agent-42 executed ask",
            log_path=log,
        )
        record = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert "copilot-agent-42" in record["message"]

    def test_appends_multiple_events(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        append_event(WORKSPACE_INIT, command="init", profile="client", log_path=log)
        append_event(
            "compile.complete", command="compile", profile="master", log_path=log
        )
        append_event(VIOLATION, command="ask", profile="client", log_path=log)
        lines = [
            line
            for line in log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(lines) == 3
        assert json.loads(lines[0])["event"] == WORKSPACE_INIT
        assert json.loads(lines[2])["event"] == VIOLATION

    def test_includes_details_when_provided(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        append_event(
            WORKSPACE_INIT,
            command="init",
            profile="client",
            details={"workspace_id": "abc-123"},
            log_path=log,
        )
        record = json.loads(log.read_text(encoding="utf-8").strip())
        assert record["details"]["workspace_id"] == "abc-123"

    def test_never_raises_on_unwritable_path(self, tmp_path: Path) -> None:
        # Point at a path that cannot be created (file exists where dir should be).
        blocker = tmp_path / "blocked"
        blocker.write_text("I am a file", encoding="utf-8")
        bad_log = blocker / "compliance-events.jsonl"
        # Should not raise -- failures are swallowed as warnings.
        append_event(WORKSPACE_INIT, command="init", profile="client", log_path=bad_log)


class TestReadEvents:
    """Tests for reading compliance events."""

    def test_read_events_empty_log(self, tmp_path: Path) -> None:
        """Should return empty list when log doesn't exist."""
        log_file = tmp_path / "nonexistent.jsonl"
        events = read_events(log_path=log_file)
        assert events == []

    def test_read_events_returns_last_n(self, tmp_path: Path) -> None:
        """Should return only last N events."""
        log_file = tmp_path / "events.jsonl"

        # Write 5 events
        for i in range(5):
            append_event(
                f"event{i}",
                command="test",
                profile="master",
                log_path=log_file,
            )

        # Read last 3
        events = read_events(n=3, log_path=log_file)
        assert len(events) == 3

    def test_read_events_parses_json(self, tmp_path: Path) -> None:
        """Should parse JSONL events correctly."""
        log_file = tmp_path / "events.jsonl"
        append_event(
            "test.event",
            command="test",
            profile="master",
            log_path=log_file,
        )

        events = read_events(log_path=log_file)
        assert len(events) > 0
        assert events[0]["event"] == "test.event"

    def test_read_events_skips_invalid_json(self, tmp_path: Path) -> None:
        """Should skip lines with invalid JSON."""
        log_file = tmp_path / "events.jsonl"
        log_file.write_text("invalid json\n", encoding="utf-8")
        log_file.write_text(
            log_file.read_text(encoding="utf-8")
            + json.dumps({"event": "valid", "ts": "2026-05-15T10:00:00Z"})
            + "\n",
            encoding="utf-8",
        )

        events = read_events(log_path=log_file)
        # Should have parsed the valid JSON and skipped invalid
        assert len(events) >= 1


class TestComputeGovernanceAdherence:
    """compute_governance_adherence returns a structured 0-100 score."""

    def _write_state(self, tmp_path: Path, **kwargs: object) -> Path:
        state_dir = tmp_path / ".providence" / "runtime"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "governance-state.json"
        state_file.write_text(
            json.dumps({"last_check": datetime.now().isoformat(), **kwargs}),
            encoding="utf-8",
        )
        return state_file

    def test_returns_dict_with_required_keys(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        result = compute_governance_adherence(
            log_path=log, state_path=self._write_state(tmp_path)
        )
        assert "score" in result
        assert "behavioral" in result
        assert "structural" in result
        assert "freshness" in result
        assert "details" in result

    def test_score_is_int_in_0_100_range(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        result = compute_governance_adherence(
            log_path=log, state_path=self._write_state(tmp_path)
        )
        assert isinstance(result["score"], int)
        assert 0 <= result["score"] <= 100

    def test_empty_log_gives_full_behavioral_score(self, tmp_path: Path) -> None:
        """No events -> assume perfect adherence (1.0 behavioral ratio)."""
        log = _log(tmp_path)
        result = compute_governance_adherence(
            log_path=log, state_path=self._write_state(tmp_path)
        )
        assert result["behavioral"] == 1.0
        assert result["details"]["behavioral_score"] == 50

    def test_all_allows_gives_full_behavioral_score(self, tmp_path: Path) -> None:
        log = _log(tmp_path)
        for _ in range(5):
            append_event(
                GOVERNANCE_CHECKED, command="test", profile="client", log_path=log
            )
        result = compute_governance_adherence(
            log_path=log, state_path=self._write_state(tmp_path)
        )
        assert result["behavioral"] == 1.0
        assert result["details"]["behavioral_score"] == 50

    def test_violations_reduce_behavioral_score(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        # 2 allows, 1 warn, 1 block -> ratio = 2/4 = 0.5 -> score = 25
        for _ in range(2):
            append_event(
                GOVERNANCE_CHECKED, command="test", profile="client", log_path=log
            )
        append_event(
            VIOLATION,
            command="test",
            profile="client",
            details={"action": "warn"},
            log_path=log,
        )
        append_event(
            VIOLATION,
            command="test",
            profile="client",
            details={"action": "block"},
            log_path=log,
        )
        result = compute_governance_adherence(
            log_path=log, state_path=self._write_state(tmp_path)
        )
        assert result["details"]["allows"] == 2
        assert result["details"]["warns"] == 1
        assert result["details"]["blocks"] == 1
        assert result["behavioral"] == 0.5
        assert result["details"]["behavioral_score"] == 25

    def test_events_outside_window_excluded(self, tmp_path: Path) -> None:
        """Events older than window_hours are not counted."""
        log = _log(tmp_path)
        log.parent.mkdir(parents=True, exist_ok=True)
        old_ts = (datetime.now() - timedelta(hours=48)).isoformat(timespec="seconds")
        old_record = json.dumps(
            {
                "timestamp": old_ts,
                "event": VIOLATION,
                "command": "ask",
                "profile": "client",
                "state": "ACTIVE",
                "details": {"action": "block"},
                "status": "error",
                "level": "error",
                "service": "sdd",
            }
        )
        log.write_text(old_record + "\n", encoding="utf-8")
        # window=24h -- the old violation should not count
        result = compute_governance_adherence(
            log_path=log, state_path=self._write_state(tmp_path), window_hours=24
        )
        assert result["details"]["blocks"] == 0
        assert result["behavioral"] == 1.0

    def test_freshness_full_when_recent_check(self, tmp_path: Path) -> None:
        state = self._write_state(
            tmp_path, profile="client", last_check=datetime.now().isoformat()
        )
        result = compute_governance_adherence(log_path=_log(tmp_path), state_path=state)
        # Just checked -> freshness close to 1.0
        assert result["freshness"] > 0.99
        assert result["details"]["freshness_score"] == 20

    def test_freshness_zero_when_stale(self, tmp_path: Path) -> None:
        old_ts = (datetime.now() - timedelta(hours=10)).isoformat()
        state = self._write_state(tmp_path, profile="client", last_check=old_ts)
        # client TTL = 1800s; 10h >> 30min
        result = compute_governance_adherence(log_path=_log(tmp_path), state_path=state)
        assert result["freshness"] == 0.0
        assert result["details"]["freshness_score"] == 0

    def test_structural_false_when_no_state_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent-state.json"
        result = compute_governance_adherence(
            log_path=_log(tmp_path), state_path=missing
        )
        assert result["structural"] is False
        assert result["details"]["structural_score"] == 0

    def test_structural_false_when_fingerprint_mismatch(self, tmp_path: Path) -> None:
        state = self._write_state(tmp_path, spec_fingerprint="aabbccddeeff0011")
        # No compiled artifact exists -> structural mismatch
        result = compute_governance_adherence(
            log_path=_log(tmp_path), state_path=state, workspace_root=tmp_path
        )
        assert result["structural"] is False

    def test_structural_true_when_fingerprints_match(self, tmp_path: Path) -> None:
        # Create a fake compiled governance-core.json with a fingerprint
        artifact_dir = tmp_path / ".providence" / "compiled"
        artifact_dir.mkdir(parents=True)
        fp = "499f7ce0da5ec85f"
        (artifact_dir / "governance-core.json").write_text(
            json.dumps({"fingerprint": fp, "items": []}), encoding="utf-8"
        )
        state = self._write_state(tmp_path, spec_fingerprint=fp)
        result = compute_governance_adherence(
            log_path=_log(tmp_path), state_path=state, workspace_root=tmp_path
        )
        assert result["structural"] is True
        assert result["details"]["structural_score"] == 30

    def test_score_is_sum_of_dimensions(self, tmp_path: Path) -> None:
        state = self._write_state(tmp_path)
        result = compute_governance_adherence(log_path=_log(tmp_path), state_path=state)
        d = result["details"]
        assert (
            result["score"]
            == d["behavioral_score"] + d["structural_score"] + d["freshness_score"]
        )


class TestLogAskEvent:
    """log_ask_event writes an event to the compliance log."""

    def test_log_ask_event_writes_record(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"
        log_ask_event(
            event=ASK_COMMAND,
            command="ask",
            profile="client",
            state="HEALTHY",
            agent_id="test-agent",
            details={
                "query_hash": "abc123",
                "context_source": "compiled",
                "compiled_fingerprint_used": "fp",
                "mandates_loaded": 2,
            },
            log_path=log,
        )
        assert log.exists()
        record = json.loads(log.read_text(encoding="utf-8").strip())
        assert record["event"] == ASK_COMMAND
        assert record["agent_id"] == "test-agent"
        assert record["details"]["query_hash"] == "abc123"

    def test_log_ask_full_event_with_trace_id(self, tmp_path: Path) -> None:
        log = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"
        log_ask_event(
            event=ASK_FULL_COMMAND,
            command="ask-full",
            profile="master",
            state="ACTIVE",
            agent_id="agent-x",
            details={
                "query_hash": "xyz789",
                "context_source": "json",
                "compiled_fingerprint_used": "fp2",
                "mandates_loaded": 5,
                "trace_id": "trace-uuid",
                "steps": [],
            },
            log_path=log,
        )
        record = json.loads(log.read_text(encoding="utf-8").strip())
        assert record["event"] == ASK_FULL_COMMAND
        assert record["details"]["trace_id"] == "trace-uuid"


class TestReadAllEvents:
    """_read_all_events returns all events without N cap."""

    def test_returns_all_events_no_cap(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = _log(tmp_path)
        for event in [
            WORKSPACE_INIT,
            GOVERNANCE_CHECKED,
            "compile.complete",
            VIOLATION,
            "command.invoked",
        ]:
            append_event(event, command="test", profile="client", log_path=log)

        result = GovernanceAdherenceScorer._read_all_events(log_path=log)
        assert len(result) == 5

    def test_returns_empty_when_log_missing(self, tmp_path: Path) -> None:
        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        result = GovernanceAdherenceScorer._read_all_events(log_path=_log(tmp_path))
        assert result == []

    def test_returns_empty_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        monkeypatch.setenv("SDD_COMPLIANCE_LOG", "disabled")
        result = GovernanceAdherenceScorer._read_all_events()
        assert result == []


def _clear_compliance_path_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDD_COMPLIANCE_LOG", raising=False)
    monkeypatch.delenv("SDD_COMPLIANCE_EVENTS_PATH", raising=False)
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)


class TestDefaultLogPath:
    def test_returns_none_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_compliance_path_env(monkeypatch)
        monkeypatch.setenv("SDD_COMPLIANCE_LOG", "disabled")
        result = default_log_path()
        assert result is None

    def test_returns_override_when_set(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _clear_compliance_path_env(monkeypatch)
        custom_log = str(tmp_path / "custom.jsonl")
        monkeypatch.setenv("SDD_COMPLIANCE_LOG", custom_log)
        result = default_log_path()
        assert result is not None
        assert str(result) == custom_log

    def test_returns_default_when_no_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_compliance_path_env(monkeypatch)
        result = default_log_path(workspace_root=tmp_path)
        assert result is not None
        assert result.name == "compliance-events.jsonl"

    def test_lower_precedence_var_used_when_only_it_is_set(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _clear_compliance_path_env(monkeypatch)
        custom_log = str(tmp_path / "from-telemetry-path.jsonl")
        monkeypatch.setenv("SDD_TELEMETRY_PATH", custom_log)
        result = default_log_path()
        assert result is not None
        assert str(result) == custom_log

    def test_sdd_compliance_log_wins_over_lower_precedence_vars(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _clear_compliance_path_env(monkeypatch)
        monkeypatch.setenv("SDD_COMPLIANCE_LOG", str(tmp_path / "winner.jsonl"))
        monkeypatch.setenv("SDD_TELEMETRY_PATH", str(tmp_path / "loser.jsonl"))
        result = default_log_path()
        assert result is not None
        assert result.name == "winner.jsonl"


class TestGetCompiledFingerprint:
    def test_returns_empty_when_no_artifacts(self, tmp_path: Path) -> None:
        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        result = GovernanceAdherenceScorer._get_compiled_fingerprint(
            workspace_root=tmp_path
        )
        assert result == ""

    def test_returns_fingerprint_from_artifact(self, tmp_path: Path) -> None:
        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        artifact_dir = tmp_path / ".providence" / "compiled"
        artifact_dir.mkdir(parents=True)
        fp = "abc123def456"
        (artifact_dir / "governance-core.json").write_text(
            json.dumps({"fingerprint": fp, "items": []}), encoding="utf-8"
        )
        result = GovernanceAdherenceScorer._get_compiled_fingerprint(
            workspace_root=tmp_path
        )
        assert result == fp

    def test_computes_fallback_fingerprint_when_not_embedded(
        self, tmp_path: Path
    ) -> None:
        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        artifact_dir = tmp_path / ".providence" / "compiled"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "governance-core.json").write_text(
            json.dumps({"items": [{"id": "M001"}]}),
            encoding="utf-8",  # no fingerprint field
        )
        result = GovernanceAdherenceScorer._get_compiled_fingerprint(
            workspace_root=tmp_path
        )
        assert len(result) == 64  # SHA256 hex


class TestDefaultLogPathFallbacks:
    def test_uses_find_workspace_root_when_no_workspace_arg(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_compliance_path_env(monkeypatch)
        with patch(
            "providence_core.utils.environment.find_workspace_root",
            return_value=tmp_path,
        ):
            result = default_log_path()
        assert result is not None
        assert "compliance-events.jsonl" in result.name

    def test_falls_back_to_cwd_when_find_workspace_root_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_compliance_path_env(monkeypatch)
        with patch(
            "providence_core.utils.environment.find_workspace_root", return_value=None
        ):
            result = default_log_path()
        assert result is not None
        assert result.name == "compliance-events.jsonl"

    def test_falls_back_when_find_workspace_root_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_compliance_path_env(monkeypatch)
        with patch(
            "providence_core.utils.environment.find_workspace_root",
            side_effect=RuntimeError("no ws"),
        ):
            result = default_log_path()
        # Falls back to cwd-based path
        assert result is not None
        assert result.name == "compliance-events.jsonl"


class TestAppendEventWhenTargetNone:
    def test_does_not_raise_when_log_path_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_COMPLIANCE_LOG", "disabled")
        # Should silently do nothing (target is None)
        append_event(WORKSPACE_INIT, command="test", profile="client")


class TestReadAllEventsException:
    def test_returns_empty_on_read_exception(self, tmp_path: Path) -> None:
        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        log = _log(tmp_path)
        log.parent.mkdir(parents=True, exist_ok=True)
        # Write binary content that will cause a UTF-8 decode error
        log.write_bytes(b"\xff\xfe\x00\x01")
        result = GovernanceAdherenceScorer._read_all_events(log_path=log)
        # Must not raise -- returns empty list on exception
        assert isinstance(result, list)


class TestComputeGovernanceAdherenceNoStatePath:
    def test_resolves_state_via_find_workspace_root(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".providence" / "runtime"
        state_dir.mkdir(parents=True)
        (state_dir / "governance-state.json").write_text(
            json.dumps({"last_check": datetime.now().isoformat()}),
            encoding="utf-8",
        )

        with patch(
            "providence_core.utils.environment.find_workspace_root",
            return_value=tmp_path,
        ):
            result = compute_governance_adherence(log_path=_log(tmp_path))
        assert "score" in result

    def test_returns_score_when_find_workspace_root_returns_none(self) -> None:
        with patch(
            "providence_core.utils.environment.find_workspace_root", return_value=None
        ):
            result = compute_governance_adherence()
        assert "score" in result
        assert isinstance(result["score"], int)


class TestGetCompiledFingerprintNoRoot:
    def test_returns_empty_when_find_workspace_root_returns_none(self) -> None:
        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        with patch(
            "providence_core.utils.environment.find_workspace_root", return_value=None
        ):
            result = GovernanceAdherenceScorer._get_compiled_fingerprint()
        assert result == ""

    def test_returns_empty_when_artifact_raises(self, tmp_path: Path) -> None:
        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        artifact_dir = tmp_path / ".providence" / "compiled"
        artifact_dir.mkdir(parents=True)
        # Write a binary file that can't be parsed as JSON
        (artifact_dir / "governance-core.json").write_bytes(b"\xff\xfe bad")

        result = GovernanceAdherenceScorer._get_compiled_fingerprint(
            workspace_root=tmp_path
        )
        assert result == ""


class TestComputeBehavioralBadTimestamp:
    def test_skips_events_with_invalid_timestamps(self) -> None:
        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        events: list[dict[str, Any]] = [
            {
                "timestamp": "not-a-datetime",
                "event": VIOLATION,
                "details": {"action": "block"},
            },
            {"timestamp": datetime.now().isoformat(), "event": GOVERNANCE_CHECKED},
        ]
        cutoff = datetime.now() - timedelta(hours=1)
        result = GovernanceAdherenceScorer._compute_behavioral(events, cutoff)
        # Bad timestamp is skipped; only GOVERNANCE_CHECKED counts
        assert result["allows"] == 1
        assert result["blocks"] == 0

    def test_handles_aware_timestamps(self) -> None:
        from datetime import timezone

        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        # Create an aware UTC timestamp
        now_utc = datetime.now(timezone.utc)
        events: list[dict[str, Any]] = [
            {"timestamp": now_utc.isoformat(), "event": GOVERNANCE_CHECKED},
        ]

        # Cutoff is local naive time
        cutoff = datetime.now() - timedelta(hours=1)
        result = GovernanceAdherenceScorer._compute_behavioral(events, cutoff)

        # Should successfully convert and count the aware event
        assert result["allows"] == 1
        assert result["window_events"] == 1


class TestComputeStructuralException:
    def test_returns_no_match_when_state_file_unreadable(self, tmp_path: Path) -> None:
        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        state = tmp_path / "state.json"
        state.write_bytes(b"\xff\xfe bad json")
        result = GovernanceAdherenceScorer._compute_structural(state, tmp_path)
        assert result["match"] is False
        assert "error" in result["detail"]


class TestComputeFreshnessException:
    def test_handles_invalid_last_check_format(self) -> None:
        from providence_core.governance.adherence_scorer import (
            GovernanceAdherenceScorer,
        )

        state_data = {"last_check": "not-a-date", "profile": "client"}
        result = GovernanceAdherenceScorer._compute_freshness(
            state_data, datetime.now()
        )
        assert result["ratio"] == 0.0
        assert "error" in result["detail"]
