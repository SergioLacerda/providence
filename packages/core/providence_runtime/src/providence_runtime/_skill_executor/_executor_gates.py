"""Pipeline gate helpers for composed skill execution."""

from __future__ import annotations

import logging
from typing import Any

from providence_skills import SkillRunResult

from ._base import ContextCarrier
from ._constants import (
    REASON_CODE_CONVERGENCE_FREEZE,
    REASON_CODE_DIAGNOSIS_INCONCLUSIVE,
)
from ._executor_results import build_escalation_result, build_execution_result

logger = logging.getLogger(__name__)


def check_diagnose_gate(**kwargs: Any) -> SkillRunResult | None:
    diagnosis_report = kwargs["carrier"].get("diagnosis_report", {})
    if not isinstance(diagnosis_report, dict):
        return None
    confidence = diagnosis_report.get("confidence", 0.0)
    min_confidence = float(
        kwargs["decision_gates"].get("diagnose_to_correct_min_confidence", 0.70)
    )
    if not (isinstance(confidence, int | float) and float(confidence) < min_confidence):
        return None
    gate_reason = REASON_CODE_DIAGNOSIS_INCONCLUSIVE
    logger.warning(
        "Pipeline gate escalation after %s: confidence %.2f < %.2f",
        "sdd-diagnose",
        float(confidence),
        min_confidence,
    )
    _push_pipeline_state(
        kwargs["carrier"],
        kwargs["parent_skill"].name,
        kwargs["stages"],
        kwargs["completed_stages"],
        kwargs["stage_results"],
        True,
        gate_reason,
        {
            "pipeline_gate_decision": {
                "from_stage": "sdd-diagnose",
                "to_stage": "sdd-correct",
                "decision": "skip_and_escalate",
                "reason_code": gate_reason,
                "confidence": float(confidence),
                "min_confidence": min_confidence,
            }
        },
    )
    return build_escalation_result(
        skill_name=kwargs["parent_skill"].name,
        profile=kwargs["profile"],
        reason=gate_reason,
        exit_code=1,
        governance_footer=kwargs["footer_fn"]("fallback_cli", "fail"),
        command_results=kwargs["command_results"],
        artifacts=kwargs["carrier"].snapshot(),
    )


def check_freeze_gate(**kwargs: Any) -> SkillRunResult | None:
    freeze_mode_state = kwargs["carrier"].get("freeze_mode_state", {})
    stage_name = kwargs["stage_name"]
    stage_capability_ids: dict[str, str | None] = (
        kwargs.get("stage_capability_ids") or {}
    )
    stage_capability_id = stage_capability_ids.get(stage_name)
    is_converge_stage = (
        stage_capability_id == "converge"
        if stage_capability_id is not None
        else stage_name == "sdd-converge"
    )
    if not (
        isinstance(freeze_mode_state, dict)
        and bool(freeze_mode_state.get("enabled"))
        and is_converge_stage
    ):
        return None
    reason = str(
        freeze_mode_state.get("trigger_reason", REASON_CODE_CONVERGENCE_FREEZE)
    )
    logger.critical(
        "Pipeline freeze escalation triggered by %s: %s", kwargs["stage_name"], reason
    )
    _push_pipeline_state(
        kwargs["carrier"],
        kwargs["parent_skill"].name,
        kwargs["stages"],
        kwargs["completed_stages"],
        kwargs["stage_results"],
        True,
        reason,
        {
            "pipeline_escalation": {
                "reason": reason,
                "trigger_stage": kwargs["stage_name"],
            }
        },
    )
    return build_escalation_result(
        skill_name=kwargs["parent_skill"].name,
        profile=kwargs["profile"],
        reason=reason,
        exit_code=2,
        governance_footer=kwargs["footer_fn"]("fallback_cli", "fail"),
        command_results=kwargs["command_results"],
        artifacts=kwargs["carrier"].snapshot(),
    )


def check_timeout_gate(**kwargs: Any) -> SkillRunResult | None:
    if kwargs["stage_result"].exit_code != 124:
        return None
    reason = f"stage_timeout:{kwargs['stage_name']}"
    logger.warning(
        "Pipeline stage timeout at %s; escalating with reason=%s",
        kwargs["stage_name"],
        reason,
    )
    _push_pipeline_state(
        kwargs["carrier"],
        kwargs["parent_skill"].name,
        kwargs["stages"],
        kwargs["completed_stages"],
        kwargs["stage_results"],
        True,
        reason,
        {"pipeline_timeout": {"reason": reason, "trigger_stage": kwargs["stage_name"]}},
    )
    return build_escalation_result(
        skill_name=kwargs["parent_skill"].name,
        profile=kwargs["profile"],
        reason=reason,
        exit_code=124,
        governance_footer=kwargs["footer_fn"]("fallback_cli", "fail"),
        command_results=kwargs["command_results"],
        artifacts=kwargs["carrier"].snapshot(),
    )


def check_stage_failure(**kwargs: Any) -> SkillRunResult | None:
    if kwargs["stage_result"].exit_code == 0:
        return None
    escalation = kwargs["stage_result"].policy_result in {
        "escalated",
        "denied",
        "blocked",
    }
    _push_pipeline_state(
        kwargs["carrier"],
        kwargs["parent_skill"].name,
        kwargs["stages"],
        kwargs["completed_stages"],
        kwargs["stage_results"],
        escalation,
        kwargs["stage_result"].reason,
    )
    return build_execution_result(
        skill_name=kwargs["parent_skill"].name,
        profile=kwargs["profile"],
        policy_result=kwargs["stage_result"].policy_result,
        reason=kwargs["stage_result"].reason,
        exit_code=kwargs["stage_result"].exit_code,
        governance_footer=kwargs["footer_fn"]("fallback_cli", "fail"),
        fallback=[],
        command_results=kwargs["command_results"],
        artifacts=kwargs["carrier"].snapshot(),
    )


def _push_pipeline_state(
    carrier: ContextCarrier,
    skill_name: str,
    stages: list[str],
    completed_stages: list[str],
    stage_results: dict[str, Any],
    escalation_triggered: bool,
    escalation_reason: str,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = {
        "pipeline_state": {
            "stages": stages,
            "completed_stages": completed_stages,
            "stage_results": stage_results,
            "escalation_triggered": escalation_triggered,
            "escalation_reason": escalation_reason,
        }
    }
    if extra:
        payload.update(extra)
    carrier.push_layer(payload, source="pipeline", skill_name=skill_name)
