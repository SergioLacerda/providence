from __future__ import annotations

from providence_runtime._skill_executor import ContextCarrier
from providence_runtime._skill_executor._constants import (
    REASON_CODE_DIAGNOSIS_INCONCLUSIVE,
)
from providence_runtime._skill_executor._executor_gates import (
    check_diagnose_gate,
    check_freeze_gate,
    check_stage_failure,
    check_timeout_gate,
)
from providence_runtime._skill_executor._executor_results import build_execution_result


def _footer(drift: str, governance: str) -> str:
    return f"{drift}:{governance}"


def test_check_diagnose_gate_escalates_below_threshold() -> None:
    carrier = ContextCarrier({"diagnosis_report": {"confidence": 0.2}})
    result = check_diagnose_gate(
        carrier=carrier,
        decision_gates={"diagnose_to_correct_min_confidence": 0.7},
        stages=["sdd-ask", "sdd-diagnose"],
        completed_stages=["sdd-ask", "sdd-diagnose"],
        stage_results={},
        parent_skill=type("Skill", (), {"name": "sdd-pipeline"})(),
        profile="default",
        command_results=[],
        footer_fn=_footer,
    )
    assert result is not None
    assert result.policy_result == "escalated"
    assert result.reason == REASON_CODE_DIAGNOSIS_INCONCLUSIVE


def test_check_freeze_gate_escalates_on_converge_stage() -> None:
    carrier = ContextCarrier({"freeze_mode_state": {"enabled": True}})
    result = check_freeze_gate(
        carrier=carrier,
        stage_name="sdd-converge",
        stages=["sdd-converge"],
        completed_stages=["sdd-converge"],
        stage_results={},
        parent_skill=type("Skill", (), {"name": "sdd-pipeline"})(),
        profile="default",
        command_results=[],
        footer_fn=_footer,
    )
    assert result is not None
    assert result.reason == "convergence.freeze_mode_active"


def test_check_timeout_gate_escalates_timeout() -> None:
    carrier = ContextCarrier()
    stage_result = build_execution_result(
        skill_name="sdd-ask",
        profile="default",
        policy_result="timeout",
        reason="timeout",
        exit_code=124,
        governance_footer="",
        fallback=[],
        command_results=[],
        artifacts={},
    )
    result = check_timeout_gate(
        carrier=carrier,
        stage_result=stage_result,
        stage_name="sdd-ask",
        stages=["sdd-ask"],
        completed_stages=["sdd-ask"],
        stage_results={},
        parent_skill=type("Skill", (), {"name": "sdd-pipeline"})(),
        profile="default",
        command_results=[],
        footer_fn=_footer,
    )
    assert result is not None
    assert result.reason == "stage_timeout:sdd-ask"


def test_check_stage_failure_returns_stage_error() -> None:
    carrier = ContextCarrier()
    stage_result = build_execution_result(
        skill_name="sdd-correct",
        profile="default",
        policy_result="blocked",
        reason="blocked",
        exit_code=1,
        governance_footer="",
        fallback=[],
        command_results=[],
        artifacts={},
    )
    result = check_stage_failure(
        carrier=carrier,
        stage_result=stage_result,
        stages=["sdd-correct"],
        completed_stages=["sdd-correct"],
        stage_results={},
        parent_skill=type("Skill", (), {"name": "sdd-pipeline"})(),
        profile="default",
        command_results=[],
        footer_fn=_footer,
    )
    assert result is not None
    assert result.policy_result == "blocked"
