"""Unit tests for providence_core.governance.compliance_record_validator."""

import pytest

from providence_core.governance.compliance_record_validator import (
    _REDACTED_PLACEHOLDER,
    ComplianceRecordValidator,
)

pytestmark = pytest.mark.unit


class TestValidateRecord:
    def test_valid_record_returns_true(self) -> None:
        record = {
            "timestamp": "2024-01-01T00:00:00Z",
            "event": "test",
            "command": "test",
            "profile": "test",
            "state": "test",
            "details": {},
            "level": "info",
            "service": "test",
            "message": "test",
            "status": "ok",
        }
        valid, missing = ComplianceRecordValidator.validate_record(record)
        assert valid is True
        assert not missing

    def test_missing_fields_returns_false(self) -> None:
        record = {"timestamp": "..."}
        valid, missing = ComplianceRecordValidator.validate_record(record)
        assert valid is False
        assert "event" in missing
        assert "command" in missing

    def test_non_dict_returns_false(self) -> None:
        valid, missing = ComplianceRecordValidator.validate_record("not-a-dict")  # type: ignore
        assert valid is False
        assert len(missing) > 0


class TestRedactSensitive:
    def test_redacts_sensitive_keys(self) -> None:
        details = {
            "api_key": "secret-123",
            "public_key": "visible-123",
            "other": "data",
        }
        redacted = ComplianceRecordValidator.redact_sensitive(details)
        assert redacted["api_key"] == _REDACTED_PLACEHOLDER
        assert redacted["public_key"] == "visible-123"
        assert redacted["other"] == "data"

    def test_returns_none_when_input_none(self) -> None:
        assert ComplianceRecordValidator.redact_sensitive(None) is None

    def test_returns_as_is_when_not_dict(self) -> None:
        assert ComplianceRecordValidator.redact_sensitive("string") == "string"  # type: ignore
