"""Compliance Record Validator - Event schema validation and sensitive data redaction.

Validates JSONL event records conform to Phase B schema and redacts sensitive fields.
"""

from typing import Any

from providence_core.constants import (
    REDACTED_PLACEHOLDER,
    REQUIRED_COMPLIANCE_RECORD_FIELDS,
    SENSITIVE_COMPLIANCE_DETAIL_KEYS,
)

__all__ = [
    "ComplianceRecordValidator",
    "_REDACTED_PLACEHOLDER",
    "_REQUIRED_RECORD_FIELDS",
]

_REQUIRED_RECORD_FIELDS = REQUIRED_COMPLIANCE_RECORD_FIELDS
_REDACTED_PLACEHOLDER = REDACTED_PLACEHOLDER


class ComplianceRecordValidator:
    """Static class for compliance record validation and redaction."""

    _REQUIRED_RECORD_FIELDS = REQUIRED_COMPLIANCE_RECORD_FIELDS
    _SENSITIVE_DETAIL_KEYS = SENSITIVE_COMPLIANCE_DETAIL_KEYS
    _REDACTED_PLACEHOLDER = REDACTED_PLACEHOLDER

    @staticmethod
    def validate_record(record: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate compliance record against Phase B schema.

        Args:
            record: Compliance event record dict

        Returns:
            Tuple of (is_valid: bool, missing_fields: list[str])
        """
        if not isinstance(record, dict):
            return False, list(REQUIRED_COMPLIANCE_RECORD_FIELDS)

        missing = [f for f in REQUIRED_COMPLIANCE_RECORD_FIELDS if f not in record]
        return len(missing) == 0, missing

    @staticmethod
    def redact_sensitive(details: dict[str, Any] | None) -> dict[str, Any] | None:
        """Redact sensitive fields from details dict.

        Creates a shallow copy and replaces sensitive keys with [REDACTED].
        Non-sensitive keys and structure are preserved.

        Args:
            details: Event details dict (may be None)

        Returns:
            Copy of details with sensitive values replaced, or None if input is None
        """
        if details is None:
            return None

        if not isinstance(details, dict):
            return details

        redacted = details.copy()
        for key in SENSITIVE_COMPLIANCE_DETAIL_KEYS:
            if key in redacted:
                redacted[key] = REDACTED_PLACEHOLDER

        return redacted
