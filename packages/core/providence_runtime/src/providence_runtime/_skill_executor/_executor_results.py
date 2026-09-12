"""Factories for `SkillRunResult` values used by the skill executor."""

from __future__ import annotations

from typing import Any

from providence_skills import SkillRunResult


def build_missing_skill_result(
    *, skill_name: str, profile: str, governance_footer: str
) -> SkillRunResult:
    return SkillRunResult(
        state="error",
        profile=profile,
        skill=skill_name,
        policy_result="missing_skill",
        reason="skill not found",
        exit_code=1,
        governance_footer=governance_footer,
        artifacts={},
    )


def build_policy_blocked_result(
    *,
    skill_name: str,
    profile: str,
    reason: str,
    drift: str,
    governance_footer: str,
    cli_fallback: list[str],
) -> SkillRunResult:
    policy_result = "unauthorized" if drift == "handshake_unauthorized" else "blocked"
    return SkillRunResult(
        state="error",
        profile=profile,
        skill=skill_name,
        policy_result=policy_result,
        reason=reason,
        exit_code=1,
        governance_footer=governance_footer,
        fallback=list(cli_fallback) if drift == "fallback_cli" else [],
        artifacts={},
    )


def build_execution_result(
    *,
    skill_name: str,
    profile: str,
    policy_result: str,
    reason: str,
    exit_code: int,
    governance_footer: str,
    fallback: list[str],
    command_results: list[dict[str, Any]],
    artifacts: dict[str, Any],
) -> SkillRunResult:
    return SkillRunResult(
        state="ok" if exit_code == 0 else "error",
        profile=profile,
        skill=skill_name,
        policy_result=policy_result,
        reason=reason,
        exit_code=exit_code,
        governance_footer=governance_footer,
        fallback=fallback,
        command_results=command_results,
        artifacts=artifacts,
    )


def build_escalation_result(
    *,
    skill_name: str,
    profile: str,
    reason: str,
    exit_code: int,
    governance_footer: str,
    command_results: list[dict[str, Any]],
    artifacts: dict[str, Any],
) -> SkillRunResult:
    return build_execution_result(
        skill_name=skill_name,
        profile=profile,
        policy_result="escalated",
        reason=reason,
        exit_code=exit_code,
        governance_footer=governance_footer,
        fallback=[],
        command_results=command_results,
        artifacts=artifacts,
    )
