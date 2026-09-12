"""Backward-compatible compliance shim."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from providence_core.governance.compliance_constants import (
    ASK_COMMAND,
    ASK_FULL_COMMAND,
    COMMAND_INVOKED,
    COMPILE_COMPLETE,
    GOVERNANCE_CHECKED,
    VIOLATION,
    WORKSPACE_INIT,
)
from providence_core.governance.compliance_log_store import (
    DEFAULT_MAX_BACKUPS,
    DEFAULT_MAX_LOG_BYTES,
    ComplianceLogStore,
)
from providence_core.governance.compliance_mode_policy import (
    _MANDATORY_EVENTS,
    LOGGING_MODE_ACTIVE,
    LOGGING_MODE_PASSIVE,
    LOGGING_MODE_STRICT,
    ComplianceModePolicy,
)
from providence_core.governance.compliance_record_validator import (
    _REDACTED_PLACEHOLDER,
    _REQUIRED_RECORD_FIELDS,
    ComplianceRecordValidator,
)

__all__ = [
    "ASK_COMMAND",
    "ASK_FULL_COMMAND",
    "COMMAND_INVOKED",
    "COMPILE_COMPLETE",
    "GOVERNANCE_CHECKED",
    "VIOLATION",
    "WORKSPACE_INIT",
    "append_event",
    "read_events",
    "log_ask_event",
    "compute_governance_adherence",
    "validate_compliance_record",
    "resolve_logging_mode",
    "rotate_compliance_log",
    "LOGGING_MODE_PASSIVE",
    "LOGGING_MODE_ACTIVE",
    "LOGGING_MODE_STRICT",
    "_REDACTED_PLACEHOLDER",
    "_REQUIRED_RECORD_FIELDS",
    "_MANDATORY_EVENTS",
    "_redact_sensitive",
    "DEFAULT_MAX_LOG_BYTES",
]


def resolve_logging_mode(profile: str = "") -> str:
    """Resolve the compliance logging mode for a workspace profile."""
    return ComplianceModePolicy.resolve_logging_mode(profile)


def _should_persist_event(event: str, logging_mode: str) -> bool:
    return ComplianceModePolicy.should_persist_event(event, logging_mode)


def _resolve_env() -> str:
    return ComplianceLogStore._resolve_env()


def validate_compliance_record(record: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a compliance record against the canonical schema."""
    return ComplianceRecordValidator.validate_record(record)


def _redact_sensitive(details: dict[str, Any] | None) -> dict[str, Any] | None:
    return ComplianceRecordValidator.redact_sensitive(details)


def rotate_compliance_log(
    log_path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_LOG_BYTES,
    max_backups: int = DEFAULT_MAX_BACKUPS,
) -> bool:
    """Rotate the compliance log when it exceeds the configured size."""
    return ComplianceLogStore.rotate(
        log_path, max_bytes=max_bytes, max_backups=max_backups
    )


def append_event(
    event: str,
    *,
    command: str,
    profile: str,
    state: str | None = None,
    details: dict[str, Any] | None = None,
    workspace_root: Path | None = None,
    log_path: Path | None = None,
    level: str = "info",
    service: str = "sdd",
    message: str = "",
    status: str = "ok",
) -> None:
    """Append a governance compliance event to persistent storage."""
    return ComplianceLogStore.append(
        event,
        command=command,
        profile=profile,
        state=state or "UNKNOWN",
        details=details or {},
        workspace_root=workspace_root,
        log_path=log_path,
        level=level,
        service=service,
        message=message,
        status=status,
    )


def read_events(
    n: int = 50, *, workspace_root: Path | None = None, log_path: Path | None = None
) -> list[dict[str, Any]]:
    """Read recent compliance events from the active log."""
    return ComplianceLogStore.read(n, workspace_root=workspace_root, log_path=log_path)


def log_ask_event(
    *,
    event: str,
    command: str,
    profile: str,
    state: str,
    agent_id: str,
    details: dict[str, Any],
    workspace_root: Path | None = None,
    log_path: Path | None = None,
) -> None:
    """Persist a normalized compliance event for `ask` command execution."""
    return ComplianceLogStore.log_ask(
        event=event,
        command=command,
        profile=profile,
        state=state,
        agent_id=agent_id,
        details=details,
        workspace_root=workspace_root,
        log_path=log_path,
    )


def compute_governance_adherence(
    *,
    workspace_root: Path | None = None,
    log_path: Path | None = None,
    state_path: Path | None = None,
    window_hours: int = 24,
) -> dict[str, Any]:
    """Compute governance adherence scores for the current workspace."""
    from providence_core.governance.adherence_scorer import GovernanceAdherenceScorer

    return GovernanceAdherenceScorer.compute(
        workspace_root=workspace_root,
        log_path=log_path,
        state_path=state_path,
        window_hours=window_hours,
    )
