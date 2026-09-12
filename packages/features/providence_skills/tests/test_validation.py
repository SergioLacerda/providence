"""Tests for providence_skills validation functions."""

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


class TestValidateSkillDefinition:
    def test_valid_skill_passes(self) -> None:
        validate_skill_definition(_VALID_SKILL)  # no exception

    def test_missing_required_field_raises(self) -> None:
        raw = {**_VALID_SKILL}
        del raw["risk_score"]
        with pytest.raises(SkillContractError, match="missing_fields"):
            validate_skill_definition(raw)

    def test_invalid_risk_score_raises(self) -> None:
        raw = {**_VALID_SKILL, "risk_score": "unknown"}
        with pytest.raises(SkillContractError, match="invalid_value:risk_score"):
            validate_skill_definition(raw)

    def test_non_list_cli_fallback_raises(self) -> None:
        raw = {**_VALID_SKILL, "cli_fallback": "providence doctor run"}
        with pytest.raises(SkillContractError, match="invalid_type:cli_fallback"):
            validate_skill_definition(raw)

    def test_non_list_outcomes_raises(self) -> None:
        raw = {**_VALID_SKILL, "outcomes": "policy_result"}
        with pytest.raises(SkillContractError, match="invalid_type:outcomes"):
            validate_skill_definition(raw)

    def test_non_list_allowed_tools_raises(self) -> None:
        raw = {**_VALID_SKILL, "allowed_tools": "providence doctor run"}
        with pytest.raises(SkillContractError, match="invalid_type:allowed_tools"):
            validate_skill_definition(raw)

    def test_non_list_required_permissions_raises(self) -> None:
        raw = {**_VALID_SKILL, "required_permissions": "workspace-read"}
        with pytest.raises(
            SkillContractError, match="invalid_type:required_permissions"
        ):
            validate_skill_definition(raw)

    def test_non_dict_validation_policy_raises(self) -> None:
        raw = {**_VALID_SKILL, "validation_policy": ["require_preflight"]}
        with pytest.raises(SkillContractError, match="invalid_type:validation_policy"):
            validate_skill_definition(raw)

    def test_all_risk_scores_accepted(self) -> None:
        for risk in ("low", "medium", "high", "critical"):
            validate_skill_definition({**_VALID_SKILL, "risk_score": risk})


class TestValidateAwakeningProfile:
    def test_valid_profile_returns_typed_instance(self) -> None:
        result = validate_awakening_profile(_VALID_PROFILE)
        assert isinstance(result, AwakeningProfile)
        assert result.activation_profile == "client"
        assert "diagnose" in result.skill_set

    def test_missing_field_raises(self) -> None:
        raw = {**_VALID_PROFILE}
        del raw["skill_set"]
        with pytest.raises(SkillContractError, match="missing_fields"):
            validate_awakening_profile(raw)

    def test_empty_fallback_order_raises(self) -> None:
        raw = {**_VALID_PROFILE, "fallback_order": []}
        with pytest.raises(SkillContractError, match="invalid_type:fallback_order"):
            validate_awakening_profile(raw)

    def test_non_list_skill_set_raises(self) -> None:
        raw = {**_VALID_PROFILE, "skill_set": "diagnose"}
        with pytest.raises(SkillContractError, match="invalid_type:skill_set"):
            validate_awakening_profile(raw)
