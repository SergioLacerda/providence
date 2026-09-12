"""Coverage tests for providence_skills.validation."""

from __future__ import annotations

import pytest

from providence_skills.contracts import AwakeningProfile, SkillContractError
from providence_skills.validation import (
    validate_awakening_profile,
    validate_skill_definition,
)

_VALID_SKILL = {
    "name": "diagnose",
    "version": "1.0.0",
    "category": "analysis",
    "description": "Diagnose workspace problems.",
    "outcomes": ["policy_result", "next_actions"],
    "execution_path": "PATH_A",
    "allowed_tools": ["providence doctor run"],
    "cli_fallback": ["providence doctor run"],
    "required_permissions": ["workspace-read"],
    "budget_policy": {"token_budget": "low"},
    "escalation_policy": {"mode": "warn"},
    "telemetry_policy": {"emit_runtime_event": True},
    "validation_policy": {"require_preflight": True},
    "risk_score": "low",
}

_VALID_PROFILE = {
    "activation_profile": "client",
    "skill_set": ["diagnose", "stabilize"],
    "fallback_order": ["diagnose"],
    "budget_policy": {"token_budget": "medium"},
    "escalation_policy": {"mode": "warn"},
    "validation_policy": {"require_preflight": True},
    "telemetry_policy": {"emit_runtime_event": True},
}


def test_validate_skill_definition_success_and_errors() -> None:
    validate_skill_definition(_VALID_SKILL)
    for key in ("name", "version", "category"):
        raw = {**_VALID_SKILL}
        raw.pop(key)
        with pytest.raises(SkillContractError):
            validate_skill_definition(raw)
    with pytest.raises(SkillContractError, match="invalid_type:cli_fallback"):
        validate_skill_definition({**_VALID_SKILL, "cli_fallback": "bad"})
    with pytest.raises(SkillContractError, match="invalid_type:outcomes"):
        validate_skill_definition({**_VALID_SKILL, "outcomes": "bad"})
    with pytest.raises(SkillContractError, match="invalid_type:allowed_tools"):
        validate_skill_definition({**_VALID_SKILL, "allowed_tools": "bad"})
    with pytest.raises(SkillContractError, match="invalid_type:required_permissions"):
        validate_skill_definition({**_VALID_SKILL, "required_permissions": "bad"})
    with pytest.raises(SkillContractError, match="invalid_type:validation_policy"):
        validate_skill_definition({**_VALID_SKILL, "validation_policy": []})
    with pytest.raises(SkillContractError, match="invalid_value:risk_score"):
        validate_skill_definition({**_VALID_SKILL, "risk_score": "weird"})


def test_validate_awakening_profile_success_and_errors() -> None:
    result = validate_awakening_profile(_VALID_PROFILE)
    assert isinstance(result, AwakeningProfile)
    raw = {**_VALID_PROFILE}
    raw.pop("skill_set")
    with pytest.raises(SkillContractError, match="missing_fields"):
        validate_awakening_profile(raw)
    with pytest.raises(SkillContractError, match="invalid_type:skill_set"):
        validate_awakening_profile({**_VALID_PROFILE, "skill_set": "bad"})
    with pytest.raises(SkillContractError, match="invalid_type:fallback_order"):
        validate_awakening_profile({**_VALID_PROFILE, "fallback_order": []})
