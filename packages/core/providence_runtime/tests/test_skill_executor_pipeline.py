from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from providence_runtime._skill_executor import (
    ContextCarrier,
    SkillExecutor,
    _get_skill_handler,
)
from providence_runtime._skill_executor._executor_gates import check_freeze_gate
from providence_runtime._skill_executor._executor_pipeline import (
    _resolve_stage_capability_ids,
)
from providence_runtime._skill_registry import SkillRegistry
from providence_runtime.skills import _REGISTRY


def _make_executor(tmp_path: Path) -> SkillExecutor:
    return SkillExecutor(SkillRegistry(_REGISTRY, tmp_path))


def test_get_skill_handler_contract_still_resolves_known_handlers() -> None:
    assert _get_skill_handler("sdd-pipeline").__class__.__name__ == "PipelineHandler"
    assert _get_skill_handler("diagnose") is None


def test_run_skill_pipeline_composes_stage_artifacts(tmp_path: Path) -> None:
    context = {
        "execution_contract": {"allowed_paths": ["safe/path"], "task_id": "task-1"},
        "diagnosis_report": {
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.95,
        },
        "diagnosis_attestation": {
            "task_id": "task-1",
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.95,
            "issued_at": "2099-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T01:00:00+00:00",
        },
        "planned_paths": ["safe/path"],
        "convergence_delta_report": {
            "alignment_score": 0.95,
            "residual_violations": [],
        },
    }
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-pipeline", context=context, project_root=tmp_path
        )
    assert result.exit_code == 0
    assert result.artifacts["pipeline_state"]["completed_stages"] == [
        "sdd-ask",
        "sdd-diagnose",
        "sdd-correct",
        "sdd-converge",
    ]


def test_run_skill_pipeline_returns_stage_escalation(tmp_path: Path) -> None:
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-pipeline", project_root=tmp_path
        )
    assert result.exit_code == 1
    assert result.policy_result == "escalated"
    assert result.artifacts["pipeline_gate_decision"]["decision"] == "skip_and_escalate"


def test_run_skill_pipeline_escalates_on_freeze_mode(tmp_path: Path) -> None:
    context = {
        "execution_contract": {"allowed_paths": ["safe/path"], "task_id": "task-2"},
        "diagnosis_report": {
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.95,
        },
        "diagnosis_attestation": {
            "task_id": "task-2",
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.95,
            "issued_at": "2099-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T01:00:00+00:00",
        },
        "planned_paths": ["safe/path"],
        "convergence_delta_report": {"alignment_score": 0.1, "residual_violations": []},
    }
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-pipeline", context=context, project_root=tmp_path
        )
    assert result.exit_code == 2
    assert (
        result.artifacts["pipeline_escalation"]["reason"]
        == "convergence.freeze_mode_active"
    )


class _FakeSkill:
    def __init__(self, capability_id: str | None) -> None:
        self.capability_id = capability_id


class _FakeRegistry:
    def __init__(self, skills: dict[str, _FakeSkill]) -> None:
        self._skills = skills

    def get_skill(self, name: str) -> _FakeSkill | None:
        return self._skills.get(name)


class _FakeParentSkill:
    name = "sdd-pipeline"


def test_resolve_stage_capability_ids_returns_none_map_without_registry() -> None:
    assert _resolve_stage_capability_ids(None, ["sdd-diagnose", "sdd-converge"]) == {
        "sdd-diagnose": None,
        "sdd-converge": None,
    }


def test_resolve_stage_capability_ids_reads_registry_skill_capability_id() -> None:
    registry = _FakeRegistry({"sdd-converge": _FakeSkill("converge")})
    result = _resolve_stage_capability_ids(registry, ["sdd-converge", "sdd-unknown"])
    assert result == {"sdd-converge": "converge", "sdd-unknown": None}


def test_check_freeze_gate_missing_registry_falls_back_to_stage_name() -> None:
    """No registry available (stage_capability_ids empty) — behaves exactly as
    the pre-Fase-3b name-based comparison did."""
    carrier = ContextCarrier({"freeze_mode_state": {"enabled": True}})
    result = check_freeze_gate(
        carrier=carrier,
        stage_name="sdd-converge",
        stage_capability_ids={},
        stages=["sdd-converge"],
        completed_stages=[],
        stage_results={},
        parent_skill=_FakeParentSkill(),
        profile="default",
        command_results=[],
        footer_fn=lambda drift, governance: "",
    )
    assert result is not None
    assert result.exit_code == 2


def test_check_freeze_gate_unmapped_capability_falls_back_to_stage_name() -> None:
    """Registry present but this stage's capability_id is None (unmapped) —
    still falls back to the name-based comparison rather than never firing."""
    carrier = ContextCarrier({"freeze_mode_state": {"enabled": True}})
    result = check_freeze_gate(
        carrier=carrier,
        stage_name="sdd-converge",
        stage_capability_ids={"sdd-converge": None},
        stages=["sdd-converge"],
        completed_stages=[],
        stage_results={},
        parent_skill=_FakeParentSkill(),
        profile="default",
        command_results=[],
        footer_fn=lambda drift, governance: "",
    )
    assert result is not None
    assert result.exit_code == 2


def test_check_freeze_gate_does_not_fire_for_non_converge_stage() -> None:
    carrier = ContextCarrier({"freeze_mode_state": {"enabled": True}})
    result = check_freeze_gate(
        carrier=carrier,
        stage_name="sdd-diagnose",
        stage_capability_ids={"sdd-diagnose": "diagnose"},
        stages=["sdd-diagnose"],
        completed_stages=[],
        stage_results={},
        parent_skill=_FakeParentSkill(),
        profile="default",
        command_results=[],
        footer_fn=lambda drift, governance: "",
    )
    assert result is None
