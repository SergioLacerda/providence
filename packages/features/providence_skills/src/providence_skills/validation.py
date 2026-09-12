"""Skill contract validation functions."""

from __future__ import annotations

from typing import Any

from .contracts import AwakeningProfile, SkillContractError

_REQUIRED_SKILL_FIELDS = [
    "name",
    "version",
    "category",
    "description",
    "outcomes",
    "execution_path",
    "allowed_tools",
    "cli_fallback",
    "required_permissions",
    "budget_policy",
    "escalation_policy",
    "telemetry_policy",
    "validation_policy",
    "risk_score",
]

_VALID_RISK_SCORES = {"low", "medium", "high", "critical", "controlled"}

_REQUIRED_AWAKENING_FIELDS = [
    "activation_profile",
    "skill_set",
    "fallback_order",
    "budget_policy",
    "escalation_policy",
    "validation_policy",
    "telemetry_policy",
]


def validate_skill_definition(raw: dict[str, Any]) -> None:
    """Validate a raw skill definition dict against the SDD skill contract."""
    missing = [key for key in _REQUIRED_SKILL_FIELDS if key not in raw]
    if missing:
        raise SkillContractError(f"missing_fields:{','.join(missing)}")
    if not isinstance(raw["cli_fallback"], list):
        raise SkillContractError("invalid_type:cli_fallback")
    if not isinstance(raw["outcomes"], list):
        raise SkillContractError("invalid_type:outcomes")
    if not isinstance(raw["allowed_tools"], list):
        raise SkillContractError("invalid_type:allowed_tools")
    if not isinstance(raw["required_permissions"], list):
        raise SkillContractError("invalid_type:required_permissions")
    if not isinstance(raw["validation_policy"], dict):
        raise SkillContractError("invalid_type:validation_policy")
    if raw["risk_score"] not in _VALID_RISK_SCORES:
        raise SkillContractError("invalid_value:risk_score")


def validate_awakening_profile(raw: dict[str, Any]) -> AwakeningProfile:
    """Validate a raw awakening profile dict and return a typed AwakeningProfile."""
    missing = [key for key in _REQUIRED_AWAKENING_FIELDS if key not in raw]
    if missing:
        raise SkillContractError(f"missing_fields:{','.join(missing)}")
    if not isinstance(raw["skill_set"], list):
        raise SkillContractError("invalid_type:skill_set")
    if not isinstance(raw["fallback_order"], list) or not raw["fallback_order"]:
        raise SkillContractError("invalid_type:fallback_order")
    return AwakeningProfile(
        activation_profile=str(raw["activation_profile"]),
        skill_set=[str(s) for s in raw["skill_set"]],
        fallback_order=[str(s) for s in raw["fallback_order"]],
        budget_policy=dict(raw["budget_policy"]),
        escalation_policy=dict(raw["escalation_policy"]),
        validation_policy=dict(raw["validation_policy"]),
        telemetry_policy=dict(raw["telemetry_policy"]),
    )
