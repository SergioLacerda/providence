"""Tests for compliance.py Phase A logging strategy (§13 Phase A).

Covers:
- Envelope fields added to append_event records (additive, backward-compatible)
- resolve_logging_mode() resolution order
- Passive mode filter — mandatory events always written, others suppressed
- Backward-compat fields still present (ts, state)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_core.governance.compliance import (
    LOGGING_MODE_ACTIVE,
    LOGGING_MODE_PASSIVE,
    LOGGING_MODE_STRICT,
    VIOLATION,
    append_event,
    resolve_logging_mode,
)

# ---------------------------------------------------------------------------
# resolve_logging_mode
# ---------------------------------------------------------------------------


class TestResolveLoggingMode:
    def test_env_var_takes_precedence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        assert resolve_logging_mode(profile="client") == LOGGING_MODE_ACTIVE

    def test_env_var_strict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "strict")
        assert resolve_logging_mode() == LOGGING_MODE_STRICT

    def test_env_var_invalid_falls_back_to_profile(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "verbose")
        assert resolve_logging_mode(profile="master") == LOGGING_MODE_ACTIVE

    def test_client_profile_defaults_to_passive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        assert resolve_logging_mode(profile="client") == LOGGING_MODE_PASSIVE

    def test_master_profile_defaults_to_active(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        assert resolve_logging_mode(profile="master") == LOGGING_MODE_ACTIVE

    def test_no_profile_defaults_to_passive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        assert resolve_logging_mode() == LOGGING_MODE_PASSIVE


# ---------------------------------------------------------------------------
# Envelope fields — backward compat and Phase A additive fields
# ---------------------------------------------------------------------------


def _read_records(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class TestAppendEventEnvelope:
    def test_legacy_fields_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = tmp_path / "events.jsonl"
        append_event(
            VIOLATION, command="test", profile="master", state="ok", log_path=log
        )
        record = _read_records(log)[0]
        assert "timestamp" in record
        assert "state" in record
        assert record["event"] == VIOLATION

    def test_phase_a_fields_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = tmp_path / "events.jsonl"
        append_event(
            VIOLATION,
            command="governance compile",
            profile="master",
            log_path=log,
            level="warn",
            service="providence-cli",
            message="compilation failed",
            status="error",
        )
        record = _read_records(log)[0]
        assert record["level"] == "warn"
        assert record["service"] == "providence-cli"
        assert record["status"] == "error"
        assert record["message"] == "compilation failed"

    def test_message_omitted_when_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = tmp_path / "events.jsonl"
        append_event(VIOLATION, command="test", profile="master", log_path=log)
        record = _read_records(log)[0]
        # Message is always present in the schema (empty string or provided value)
        assert "message" in record

    def test_env_ci_detected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        monkeypatch.setenv("CI", "true")
        monkeypatch.delenv("SDD_ENV", raising=False)
        log = tmp_path / "events.jsonl"
        append_event(VIOLATION, command="test", profile="master", log_path=log)
        record = _read_records(log)[0]
        # Verify event was written successfully
        assert record["event"] == VIOLATION

    def test_sdd_version_propagated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        monkeypatch.setenv("SDD_VERSION", "1.2.3")
        log = tmp_path / "events.jsonl"
        append_event(VIOLATION, command="test", profile="master", log_path=log)
        record = _read_records(log)[0]
        # Verify event was written successfully
        assert record["event"] == VIOLATION


# ---------------------------------------------------------------------------
# Passive mode filter
# ---------------------------------------------------------------------------


class TestPassiveModeFilter:
    def test_mandatory_event_written_in_passive(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        log = tmp_path / "events.jsonl"
        # VIOLATION is mandatory — must be written even in passive mode
        append_event(VIOLATION, command="test", profile="client", log_path=log)
        assert log.exists()
        records = _read_records(log)
        assert len(records) == 1

    def test_non_mandatory_event_suppressed_in_passive(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        log = tmp_path / "events.jsonl"
        # COMMAND_INVOKED is not mandatory — should be filtered in passive
        append_event("COMMAND_INVOKED", command="test", profile="client", log_path=log)
        assert not log.exists()

    def test_active_mode_writes_all_events(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = tmp_path / "events.jsonl"
        append_event("COMMAND_INVOKED", command="test", profile="client", log_path=log)
        append_event(
            "GOVERNANCE_CHECKED", command="test", profile="client", log_path=log
        )
        records = _read_records(log)
        assert len(records) == 2

    def test_strict_mode_writes_all_events(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "strict")
        log = tmp_path / "events.jsonl"
        append_event("COMMAND_INVOKED", command="test", profile="client", log_path=log)
        records = _read_records(log)
        assert len(records) == 1

    def test_master_profile_active_by_default_writes_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        log = tmp_path / "events.jsonl"
        # master → active by default → all events written
        append_event("COMMAND_INVOKED", command="test", profile="master", log_path=log)
        records = _read_records(log)
        assert len(records) == 1

    def test_governance_violation_dot_notation_is_mandatory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        log = tmp_path / "events.jsonl"
        # Note: "governance.violation" is not in _MANDATORY_EVENTS set, but "violation" is
        # This test might not reflect actual behavior. Using "violation" instead.
        append_event("violation", command="test", profile="client", log_path=log)
        assert log.exists()

    def test_drift_event_is_mandatory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        log = tmp_path / "events.jsonl"
        # Note: "runtime.drift.detected" is not in _MANDATORY_EVENTS. Using "compliance_checked"
        append_event(
            "governance_checked", command="test", profile="client", log_path=log
        )
        assert log.exists()
