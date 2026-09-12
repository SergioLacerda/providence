"""Skill contract types — extracted to break skills ↔ policy cyclic import.

This module defines the skill capability contracts used throughout the SDD runtime.
It is isolated as a leaf module to prevent circular dependencies between skills.py
and policy.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

SkillStatus = Literal["active", "deprecated"]
RiskScore = Literal["low", "medium", "high", "critical", "controlled"]

TOKEN_BUDGET_MEDIUM = "medium"  # nosec B105
TOKEN_BUDGET_LOW = "low"  # nosec B105


def _is_deprecation_due(deprecated_after: str | None) -> bool:
    if not deprecated_after:
        return False
    try:
        due_at = datetime.fromisoformat(deprecated_after.replace("Z", "+00:00"))
    except ValueError:
        return False
    return due_at <= datetime.now(timezone.utc)


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    version: str
    category: str
    description: str
    when_to_use: list[str]
    outcomes: list[str]
    allowed_tools: list[str]
    cli_fallback: list[str]
    required_permissions: list[str]
    capability_id: str | None = None  # nova_arquitetura.txt §7 — Capability ≠ Skill
    execution_path: str = "PATH_A"
    status: SkillStatus = "active"
    deprecated_after: str | None = None
    sunset_after: str | None = None
    risk_score: RiskScore = "medium"
    tags: list[str] = field(default_factory=list)
    budget_policy: dict[str, Any] = field(
        default_factory=lambda: {
            "token_budget": TOKEN_BUDGET_MEDIUM,
            "timeout_seconds": 120,
            "max_retries": 1,
        }
    )
    escalation_policy: dict[str, Any] = field(
        default_factory=lambda: {
            "mode": "warn",
            "require_human_on": ["critical_violation", "repeat_failure"],
        }
    )
    telemetry_policy: dict[str, Any] = field(
        default_factory=lambda: {
            "emit_runtime_event": True,
            "otel_required_if_enabled": True,
        }
    )
    validation_policy: dict[str, Any] = field(
        default_factory=lambda: {
            "require_preflight": True,
            "require_postcheck": True,
        }
    )
    # V6 fields — WCE enrichment (skillsV6.md §3.2)
    triggers: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    fallback_to: str | None = None
    idempotent: bool = False
    context_policy: dict[str, Any] = field(
        default_factory=lambda: {
            "max_context_tokens": 1800,
            "default_detail": "minimal",
        }
    )
    config: dict[str, Any] = field(default_factory=dict)
    # Plugin delegation — M017 Analysis Plugin Compliance
    delegation_policy: dict[str, Any] | None = None
    # Hard-mode governance enforcement (M010, M015)
    hard_mode_protocol: dict[str, Any] | None = None
    hard_mode_invariants: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema_version"] = "1.1.0"
        payload["deprecation_due"] = _is_deprecation_due(self.deprecated_after)
        for key in ("hard_mode_protocol", "hard_mode_invariants"):
            if payload.get(key) is None:
                payload.pop(key, None)
        return payload

    def to_yaml(self) -> str:
        """Serialize skill definition to YAML format.

        Returns:
            YAML string representation of the skill

        Raises:
            ImportError: If PyYAML is not installed
        """
        if yaml is None:
            raise ImportError(
                "PyYAML is required for YAML serialization. Install with: pip install pyyaml"
            )

        payload = self.to_dict()
        return yaml.dump(payload, default_flow_style=False, sort_keys=False)


__all__ = [
    "SkillDefinition",
    "SkillStatus",
    "RiskScore",
    "TOKEN_BUDGET_LOW",
    "TOKEN_BUDGET_MEDIUM",
    "_is_deprecation_due",
]
