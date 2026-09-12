"""Public skill execution contracts.

Lightweight types shared across packages that need skill execution results
without importing the full providence_runtime engine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AwakeningProfile:
    """Validated awakening profile for skill orchestration."""

    activation_profile: str
    skill_set: list[str]
    fallback_order: list[str]
    budget_policy: dict[str, Any]
    escalation_policy: dict[str, Any]
    validation_policy: dict[str, Any]
    telemetry_policy: dict[str, Any]


@dataclass(frozen=True)
class SkillRunResult:
    """Result produced by a skill execution."""

    state: str
    profile: str
    skill: str
    policy_result: str
    reason: str
    exit_code: int
    governance_footer: str = ""
    fallback: list[str] = field(default_factory=list)
    command_results: list[dict[str, Any]] = field(default_factory=list)
    trace_id: str = ""
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return asdict(self)


class SkillContractError(ValueError):
    """Raised when skill or awakening contracts are invalid."""


class UnauthorizedSkillError(RuntimeError):
    """Raised when a skill is not authorized to run."""
