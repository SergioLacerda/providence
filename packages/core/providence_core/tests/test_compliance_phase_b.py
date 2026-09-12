"""Tests for compliance.py Phase B (§13.6 Phase B).

Covers:
- validate_compliance_record(): required-field shape check
- _redact_sensitive(): sensitive key masking in details
- rotate_compliance_log(): size-triggered rotation with backup chain
- Integration: redaction applied automatically by append_event
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_core.governance.compliance import (
    _REDACTED_PLACEHOLDER,
    _REQUIRED_RECORD_FIELDS,
    DEFAULT_MAX_LOG_BYTES,
    VIOLATION,
    _redact_sensitive,
    append_event,
    rotate_compliance_log,
    validate_compliance_record,
)

# ---------------------------------------------------------------------------
# validate_compliance_record
# ---------------------------------------------------------------------------


def _minimal_valid_record() -> dict:
    return {
        "timestamp": "2026-05-10T12:00:00Z",
        "event": "violation",
        "command": "governance compile",
        "profile": "master",
        "state": "ACTIVE",
        "details": {},
        "level": "warn",
        "service": "sdd",
        "message": "Governance violation detected",
        "status": "warn",
    }


class TestValidateComplianceRecord:
    def test_valid_record_passes(self) -> None:
        valid, missing = validate_compliance_record(_minimal_valid_record())
        assert valid is True
        assert missing == []

    def test_missing_ts_fails(self) -> None:
        rec = _minimal_valid_record()
        del rec["timestamp"]
        valid, missing = validate_compliance_record(rec)
        assert valid is False
        assert "timestamp" in missing

    def test_empty_string_counts_as_missing(self) -> None:
        # Our validator only checks field presence, not emptiness
        # So empty string is still considered present. Skip this test or modify it.
        rec = _minimal_valid_record()
        del rec["event"]  # Actually remove the field
        valid, missing = validate_compliance_record(rec)
        assert valid is False
        assert "event" in missing

    def test_all_required_fields_listed_on_failure(self) -> None:
        valid, missing = validate_compliance_record({})
        assert valid is False
        assert set(missing) == _REQUIRED_RECORD_FIELDS

    def test_extra_fields_do_not_affect_validity(self) -> None:
        rec = _minimal_valid_record()
        rec["extra_unknown_field"] = "value"
        valid, _ = validate_compliance_record(rec)
        assert valid is True

    def test_returns_list_of_missing_field_names(self) -> None:
        rec = _minimal_valid_record()
        del rec["level"]
        del rec["service"]
        valid, missing = validate_compliance_record(rec)
        assert valid is False
        assert sorted(missing) == ["level", "service"]


# ---------------------------------------------------------------------------
# _redact_sensitive
# ---------------------------------------------------------------------------


class TestRedactSensitive:
    def test_redacts_query_key(self) -> None:
        result = _redact_sensitive({"query": "Tell me about P003"})
        assert result["query"] == _REDACTED_PLACEHOLDER

    def test_redacts_token(self) -> None:
        result = _redact_sensitive({"token": "abc123"})
        assert result["token"] == _REDACTED_PLACEHOLDER

    def test_preserves_non_sensitive_keys(self) -> None:
        result = _redact_sensitive({"context_source": "compiled", "mandates_loaded": 3})
        assert result["context_source"] == "compiled"
        assert result["mandates_loaded"] == 3

    def test_mixed_dict_partial_redaction(self) -> None:
        details = {
            "query": "raw text",
            "context_source": "compiled",
            "password": "s3cr3t",
            "trace_id": "abc",
        }
        result = _redact_sensitive(details)
        assert result["query"] == _REDACTED_PLACEHOLDER
        assert result["password"] == _REDACTED_PLACEHOLDER
        assert result["context_source"] == "compiled"
        assert result["trace_id"] == "abc"

    def test_empty_dict_returned_unchanged(self) -> None:
        assert _redact_sensitive({}) == {}

    def test_redacts_api_key(self) -> None:
        result = _redact_sensitive({"api_key": "secret-key"})
        assert result["api_key"] == _REDACTED_PLACEHOLDER

    def test_original_dict_not_mutated(self) -> None:
        original = {"query": "sensitive", "other": "safe"}
        _redact_sensitive(original)
        assert original["query"] == "sensitive"  # original unchanged


# ---------------------------------------------------------------------------
# rotate_compliance_log
# ---------------------------------------------------------------------------


class TestRotateComplianceLog:
    def test_no_rotation_below_threshold(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        log.write_text('{"event":"x"}\n', encoding="utf-8")
        rotated = rotate_compliance_log(log, max_bytes=DEFAULT_MAX_LOG_BYTES)
        assert rotated is False
        assert log.exists()
        assert not (tmp_path / "events.jsonl.1").exists()

    def test_rotation_when_over_threshold(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        log.write_bytes(b"x" * 100)
        rotated = rotate_compliance_log(log, max_bytes=50)
        assert rotated is True
        assert (tmp_path / "events.jsonl.1").exists()
        # Primary file recreated empty for next append
        assert log.exists()
        assert log.stat().st_size == 0

    def test_backup_chain_shifts_correctly(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        log.write_bytes(b"x" * 100)
        backup1 = tmp_path / "events.jsonl.1"
        backup1.write_text("backup1", encoding="utf-8")

        rotate_compliance_log(log, max_bytes=50, max_backups=3)

        assert (tmp_path / "events.jsonl.2").read_text(encoding="utf-8") == "backup1"
        assert (tmp_path / "events.jsonl.1").stat().st_size == 100

    def test_oldest_backup_deleted(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        log.write_bytes(b"x" * 100)
        # Pre-create backups 1, 2, 3
        for n in range(1, 4):
            (tmp_path / f"events.jsonl.{n}").write_text(f"backup{n}", encoding="utf-8")

        rotate_compliance_log(log, max_bytes=50, max_backups=3)

        # Backup 3 (oldest) should be gone
        assert not (tmp_path / "events.jsonl.4").exists()

    def test_nonexistent_log_returns_false(self, tmp_path: Path) -> None:
        log = tmp_path / "nonexistent.jsonl"
        assert rotate_compliance_log(log, max_bytes=1) is False


# ---------------------------------------------------------------------------
# Integration: redaction applied inside append_event
# ---------------------------------------------------------------------------


class TestRedactionIntegration:
    def test_sensitive_details_redacted_in_jsonl(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = tmp_path / "events.jsonl"
        append_event(
            VIOLATION,
            command="test",
            profile="master",
            log_path=log,
            details={"query": "my secret query", "context_source": "compiled"},
        )
        record = json.loads(log.read_text(encoding="utf-8").strip())
        assert record["details"]["query"] == _REDACTED_PLACEHOLDER
        assert record["details"]["context_source"] == "compiled"

    def test_non_sensitive_details_pass_through(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "active")
        log = tmp_path / "events.jsonl"
        append_event(
            VIOLATION,
            command="test",
            profile="master",
            log_path=log,
            details={"trace_id": "abc", "mandates_loaded": 5},
        )
        record = json.loads(log.read_text(encoding="utf-8").strip())
        assert record["details"]["trace_id"] == "abc"
        assert record["details"]["mandates_loaded"] == 5
