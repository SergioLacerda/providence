"""Data models for registry reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ReconciliationError(ValueError):
    """Raised when canonical artifacts are invalid or inconsistent."""


@dataclass(frozen=True)
class ReconciliationSummary:
    """Reconciliation result counters for commands and skills."""

    commands: dict[str, int]
    skills: dict[str, int]
    drift_detected: bool = False

    def as_json(self) -> dict[str, Any]:
        """Serialize reconciliation counters for command output."""
        return {
            "commands": self.commands,
            "skills": self.skills,
            "drift_detected": self.drift_detected,
            "errors": [],
        }
