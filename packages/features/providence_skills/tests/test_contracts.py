"""Tests for providence_skills contracts."""

import pytest

from providence_skills.contracts import (
    AwakeningProfile,
    SkillContractError,
    SkillRunResult,
    UnauthorizedSkillError,
)
from providence_skills.formatter import format_governance_footer


class TestSkillRunResult:
    def test_to_dict_returns_all_fields(self) -> None:
        result = SkillRunResult(
            state="ok",
            profile="client",
            skill="diagnose",
            policy_result="PASS",
            reason="all checks passed",
            exit_code=0,
            governance_footer="PROVIDENCE GOVERNANCE: drift=none | governance=ok | profile=diagnose",
        )
        d = result.to_dict()
        assert d["state"] == "ok"
        assert d["skill"] == "diagnose"
        assert d["exit_code"] == 0
        assert d["governance_footer"].startswith("PROVIDENCE GOVERNANCE")

    def test_defaults_are_empty(self) -> None:
        result = SkillRunResult(
            state="ok",
            profile="client",
            skill="diagnose",
            policy_result="PASS",
            reason="",
            exit_code=0,
        )
        assert result.fallback == []
        assert result.command_results == []
        assert result.trace_id == ""


class TestAwakeningProfile:
    def test_is_frozen(self) -> None:
        profile = AwakeningProfile(
            activation_profile="client",
            skill_set=["diagnose"],
            fallback_order=["diagnose"],
            budget_policy={"token_budget": "low"},
            escalation_policy={"mode": "warn"},
            validation_policy={"require_preflight": True},
            telemetry_policy={"emit_runtime_event": True},
        )
        with pytest.raises(AttributeError):
            profile.activation_profile = "other"  # type: ignore[misc]


class TestErrors:
    def test_skill_contract_error_is_value_error(self) -> None:
        err = SkillContractError("missing_fields:name")
        assert isinstance(err, ValueError)

    def test_unauthorized_skill_error_is_runtime_error(self) -> None:
        err = UnauthorizedSkillError("skill not authorized")
        assert isinstance(err, RuntimeError)


class TestFormatGovernanceFooter:
    def test_canonical_format(self) -> None:
        footer = format_governance_footer(
            drift="none", governance="ok", profile="diagnose"
        )
        assert (
            footer
            == "PROVIDENCE GOVERNANCE: drift=none | governance=ok | profile=diagnose"
        )
