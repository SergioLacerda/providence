"""Pipeline orchestration for composed skill execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from providence_skills import SkillRunResult, format_governance_footer

from ._base import ContextCarrier
from ._executor_gates import (
    check_diagnose_gate,
    check_freeze_gate,
    check_stage_failure,
    check_timeout_gate,
)
from ._executor_results import build_execution_result
from ._handlers import _prepare_pipeline_stages


def _resolve_stage_capability_ids(
    registry: Any, stages: list[str]
) -> dict[str, str | None]:
    """Resolve each stage's capability_id once per pipeline run; never raises."""
    resolved: dict[str, str | None] = {}
    for stage_name in stages:
        capability_id = None
        if registry is not None:
            skill = registry.get_skill(stage_name)
            if skill is not None:
                capability_id = getattr(skill, "capability_id", None)
        resolved[stage_name] = capability_id
    return resolved


def run_composed_skill(
    *,
    run_skill: Callable[..., SkillRunResult],
    parent_skill: Any,
    context: dict[str, Any],
    seed_artifacts: dict[str, Any],
    compose_config: dict[str, Any],
    execute: bool,
    profile: str,
    enforcement_mode: str,
    project_root: Any,
    registry: Any = None,
    footer_fn: Callable[[str, str], str] | None = None,
) -> SkillRunResult:
    carrier = ContextCarrier(context)
    if seed_artifacts:
        carrier.push_layer(
            seed_artifacts, source="handler", skill_name=parent_skill.name
        )
    decision_gates = compose_config.get("decision_gates", {})
    stages, completed_stages, stage_results = _prepare_pipeline_stages(
        carrier, compose_config
    )
    stage_capability_ids = _resolve_stage_capability_ids(registry, stages)
    command_results: list[dict[str, Any]] = []
    footer = footer_fn or (
        lambda drift, governance: format_governance_footer(
            drift=drift, governance=governance, profile=profile
        )
    )
    for stage_name in stages:
        stage_result = run_skill(
            stage_name,
            execute=execute,
            profile=profile,
            enforcement_mode=enforcement_mode,
            project_root=project_root,
            context=carrier.snapshot(),
        )
        command_results.extend(stage_result.command_results)
        _record_stage(
            carrier,
            parent_skill.name,
            stages,
            completed_stages,
            stage_results,
            stage_name,
            stage_result,
        )
        if stage_result.artifacts:
            carrier.push_layer(
                stage_result.artifacts, source="skill", skill_name=stage_name
            )
        is_diagnose_stage = (
            stage_capability_ids.get(stage_name) == "diagnose"
            if stage_capability_ids.get(stage_name) is not None
            else stage_name == "sdd-diagnose"
        )
        if is_diagnose_stage:
            result = check_diagnose_gate(
                carrier=carrier,
                decision_gates=decision_gates,
                stages=stages,
                completed_stages=completed_stages,
                stage_results=stage_results,
                parent_skill=parent_skill,
                profile=profile,
                command_results=command_results,
                footer_fn=footer,
            )
            if result is not None:
                return result
        for result in (
            check_freeze_gate(
                carrier=carrier,
                stage_name=stage_name,
                stage_capability_ids=stage_capability_ids,
                stages=stages,
                completed_stages=completed_stages,
                stage_results=stage_results,
                parent_skill=parent_skill,
                profile=profile,
                command_results=command_results,
                footer_fn=footer,
            ),
            check_timeout_gate(
                carrier=carrier,
                stage_result=stage_result,
                stage_name=stage_name,
                stages=stages,
                completed_stages=completed_stages,
                stage_results=stage_results,
                parent_skill=parent_skill,
                profile=profile,
                command_results=command_results,
                footer_fn=footer,
            ),
            check_stage_failure(
                carrier=carrier,
                stage_result=stage_result,
                stages=stages,
                completed_stages=completed_stages,
                stage_results=stage_results,
                parent_skill=parent_skill,
                profile=profile,
                command_results=command_results,
                footer_fn=footer,
            ),
        ):
            if result is not None:
                return result
    return build_execution_result(
        skill_name=parent_skill.name,
        profile=profile,
        policy_result="executed" if execute else "planned",
        reason="pipeline execution completed"
        if execute
        else "pipeline dry-run planning completed",
        exit_code=0,
        governance_footer=footer("fallback_cli" if execute else "none", "ok"),
        fallback=[],
        command_results=command_results,
        artifacts=carrier.snapshot(),
    )


def _record_stage(
    carrier: ContextCarrier,
    skill_name: str,
    stages: list[str],
    completed_stages: list[str],
    stage_results: dict[str, Any],
    stage_name: str,
    stage_result: SkillRunResult,
) -> None:
    stage_results[stage_name] = {
        "state": stage_result.state,
        "policy_result": stage_result.policy_result,
        "reason": stage_result.reason,
        "exit_code": stage_result.exit_code,
    }
    completed_stages.append(stage_name)
    carrier.push_layer(
        {
            "pipeline_state": {
                "stages": stages,
                "completed_stages": completed_stages,
                "stage_results": stage_results,
                "escalation_triggered": False,
                "escalation_reason": "",
            }
        },
        source="pipeline",
        skill_name=skill_name,
    )
