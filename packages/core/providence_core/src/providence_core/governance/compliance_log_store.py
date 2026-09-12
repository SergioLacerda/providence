"""Compliance log persistence and rotation."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providence_core.governance.compliance_constants import default_log_path
from providence_core.governance.compliance_mode_policy import ComplianceModePolicy
from providence_core.governance.compliance_record_validator import (
    ComplianceRecordValidator,
)

DEFAULT_MAX_LOG_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_BACKUPS = 3


def _resolved_workspace_root(workspace_root: Path | None) -> Path:
    if workspace_root is not None:
        return workspace_root
    from providence_core.utils.environment import find_workspace_root

    return find_workspace_root() or Path.cwd()


class ComplianceLogStore:
    """Persist, rotate, and read governance compliance events."""

    DEFAULT_MAX_LOG_BYTES = DEFAULT_MAX_LOG_BYTES
    DEFAULT_MAX_BACKUPS = DEFAULT_MAX_BACKUPS

    @staticmethod
    def _resolve_env() -> str:
        if os.environ.get("CI") in {"1", "true", "True"}:
            return "ci"
        return os.environ.get("SDD_ENV", "").strip().lower() or "dev"

    @staticmethod
    def rotate(
        log_path: Path,
        *,
        max_bytes: int = DEFAULT_MAX_LOG_BYTES,
        max_backups: int = DEFAULT_MAX_BACKUPS,
    ) -> bool:
        """Rotate the compliance log file when it exceeds the size threshold."""
        if not log_path.exists() or log_path.stat().st_size < max_bytes:
            return False
        try:
            for index in range(max_backups - 1, 0, -1):
                old, new = (
                    log_path.with_name(f"{log_path.name}.{index}"),
                    log_path.with_name(f"{log_path.name}.{index + 1}"),
                )
                if old.exists():
                    old.rename(new)
            log_path.rename(log_path.with_name(f"{log_path.name}.1"))
            log_path.touch()
            return True
        except Exception:
            return False

    @staticmethod
    def append(
        event: str,
        *,
        command: str,
        profile: str,
        state: str,
        details: dict[str, Any],
        agent_id: str = "",
        workspace_root: Path | None = None,
        log_path: Path | None = None,
        level: str = "info",
        service: str = "sdd",
        message: str = "",
        status: str = "ok",
    ) -> None:
        """Append a validated compliance record to the active log file."""
        workspace_root = _resolved_workspace_root(workspace_root)
        target = log_path or default_log_path(workspace_root)
        if target is None:
            return
        mode = ComplianceModePolicy.resolve_logging_mode(profile)
        if not ComplianceModePolicy.should_persist_event(event, mode):
            return
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "command": command,
            "profile": profile,
            "state": state,
            "agent_id": agent_id or os.environ.get("SDD_AGENT_ID", ""),
            "details": ComplianceRecordValidator.redact_sensitive(details),
            "level": level,
            "service": service,
            "message": message,
            "status": status,
        }
        valid, missing = ComplianceRecordValidator.validate_record(record)
        if not valid:
            logging.warning("Invalid compliance record, missing fields: %s", missing)
            return
        ComplianceLogStore.rotate(
            target, max_bytes=DEFAULT_MAX_LOG_BYTES, max_backups=DEFAULT_MAX_BACKUPS
        )
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")
        except Exception as exc:
            logging.error("Failed to write compliance event: %s", exc)

    @staticmethod
    def read(
        n: int = 50, *, workspace_root: Path | None = None, log_path: Path | None = None
    ) -> list[dict[str, Any]]:
        """Read compliance events from disk, optionally capped to the last `n`."""
        target = log_path or default_log_path(_resolved_workspace_root(workspace_root))
        if target is None or not target.exists():
            return []
        try:
            events = []
            with open(target, encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return events if n <= 0 else events[-n:]
        except Exception:
            return []

    @staticmethod
    def log_ask(
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
        """Append a normalized compliance record for an ask command invocation."""
        ComplianceLogStore.append(
            event,
            command=command,
            profile=profile,
            state=state,
            agent_id=agent_id,
            details=details,
            workspace_root=workspace_root,
            log_path=log_path,
            level="info",
            service="sdd",
            message=f"Agent {agent_id} executed {command}",
            status="ok",
        )
