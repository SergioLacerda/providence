"""Shared SDD core constants."""

from __future__ import annotations

LOGGING_MODE_PASSIVE = "passive"
LOGGING_MODE_ACTIVE = "active"
LOGGING_MODE_STRICT = "strict"
VALID_LOGGING_MODES = {
    LOGGING_MODE_PASSIVE,
    LOGGING_MODE_ACTIVE,
    LOGGING_MODE_STRICT,
}
MANDATORY_COMPLIANCE_EVENTS = {
    "violation",
    "workspace_init",
    "compile_complete",
    "governance_checked",
}
REQUIRED_COMPLIANCE_RECORD_FIELDS = {
    "timestamp",
    "event",
    "command",
    "profile",
    "state",
    "details",
    "level",
    "service",
    "message",
    "status",
}
SENSITIVE_COMPLIANCE_DETAIL_KEYS = {
    "query",
    "token",
    "api_key",
    "password",
    "secret",
    "credential",
    "auth",
    "signature",
    "private_key",
}
REDACTED_PLACEHOLDER = "[REDACTED]"
