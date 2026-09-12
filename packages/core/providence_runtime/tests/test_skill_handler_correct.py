from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from providence_runtime._skill_executor import (
    CorrectHandler,
    _evaluate_correction_gate,
    _evaluate_gate_expression,
    _load_gate_rules,
)

# ---------------------------------------------------------------------------
# _evaluate_correction_gate unit tests
# ---------------------------------------------------------------------------


def _ctx(
    *,
    evidence: list = (),
    confidence: float = 0.9,
    allowed: list = ("safe/",),
    planned: list = (),
) -> dict:
    task_id = "task-1"
    return {
        "diagnosis_report": {
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": list(evidence),
            "confidence": confidence,
        },
        "execution_contract": {"allowed_paths": list(allowed), "task_id": task_id},
        "diagnosis_attestation": {
            "task_id": task_id,
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": list(evidence),
            "confidence": confidence,
            "issued_at": "2099-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T01:00:00+00:00",
        },
        "planned_paths": list(planned),
    }


def test_gate_escalates_when_evidence_missing() -> None:
    result = _evaluate_correction_gate(_ctx(evidence=[]), active_rules=[])
    assert result["decision"] == "escalate"
    assert result["reason_code"] == "evidence.insufficient"


def test_gate_escalates_when_confidence_too_low() -> None:
    result = _evaluate_correction_gate(
        _ctx(evidence=["e"], confidence=0.5), active_rules=[]
    )
    assert result["decision"] == "escalate"
    assert result["reason_code"] == "diagnosis.inconclusive"


def test_gate_denies_when_no_allowed_paths() -> None:
    result = _evaluate_correction_gate(
        _ctx(evidence=["e"], confidence=0.9, allowed=[]), active_rules=[]
    )
    assert result["decision"] == "deny"
    assert result["reason_code"] == "contract.missing_or_invalid"


def test_gate_denies_on_scope_violation() -> None:
    result = _evaluate_correction_gate(
        _ctx(evidence=["e"], confidence=0.9, allowed=["safe/"], planned=["unsafe/"]),
        active_rules=[],
    )
    assert result["decision"] == "deny"
    assert result["reason_code"] == "scope.violation"


def test_gate_denies_when_matching_active_rule() -> None:
    active_rules = [{"pattern": "h|r", "status": "active"}]
    result = _evaluate_correction_gate(
        _ctx(evidence=["e"], confidence=0.9), active_rules=active_rules
    )
    assert result["decision"] == "deny"
    assert result["reason_code"] == "rule.blocked"


def test_gate_priority_uses_first_matching_rule() -> None:
    rules = [
        {
            "id": "first",
            "priority": 5,
            "when": {"fact": "always"},
            "decision": "deny",
            "reason_code": "first",
            "next_action": "stop",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "second",
            "priority": 10,
            "when": {"fact": "always"},
            "decision": "allow",
            "reason_code": "second",
            "next_action": "go",
            "requires_human_review": False,
            "escalate_to_human": False,
        },
    ]
    result = _evaluate_correction_gate(
        _ctx(evidence=["e"]), active_rules=[], gate_rules=rules
    )
    assert result["decision"] == "deny"
    assert result["reason_code"] == "first"


def test_gate_allows_valid_context() -> None:
    result = _evaluate_correction_gate(
        _ctx(evidence=["e"], confidence=0.9, allowed=["safe/"], planned=["safe/"]),
        active_rules=[],
    )
    assert result["decision"] == "allow"
    assert result["reason_code"] == "ok"


def test_gate_escalates_when_attestation_missing() -> None:
    ctx = _ctx(evidence=["e"], confidence=0.9)
    ctx.pop("diagnosis_attestation")
    result = _evaluate_correction_gate(ctx, active_rules=[])
    assert result["decision"] == "escalate"
    assert result["reason_code"] == "diagnosis.missing"


def test_gate_denies_when_attestation_stale() -> None:
    ctx = _ctx(evidence=["e"], confidence=0.9)
    ctx["diagnosis_attestation"]["expires_at"] = "2000-01-01T00:00:00+00:00"
    result = _evaluate_correction_gate(ctx, active_rules=[])
    assert result["decision"] == "deny"
    assert result["reason_code"] == "diagnosis.stale"


def test_gate_denies_when_contract_stale() -> None:
    ctx = _ctx(evidence=["e"], confidence=0.9)
    ctx["execution_contract"]["expires_at"] = "2000-01-01T00:00:00+00:00"
    result = _evaluate_correction_gate(ctx, active_rules=[])
    assert result["decision"] == "deny"
    assert result["reason_code"] == "contract.missing_or_invalid"


def test_gate_denies_when_freeze_mode_active() -> None:
    ctx = _ctx(evidence=["e"], confidence=0.9)
    ctx["freeze_mode_state"] = {"enabled": True}
    result = _evaluate_correction_gate(ctx, active_rules=[])
    assert result["decision"] == "deny"
    assert result["reason_code"] == "convergence.freeze_mode_active"


def test_gate_expression_supports_nested_boolean_logic() -> None:
    facts = {
        "attestation": {"present": True, "confidence": 0.4},
        "contract": {"min_diagnosis_confidence": 0.8},
    }
    expression = {
        "all": [
            {"fact": "attestation.present"},
            {
                "lt": {
                    "left": {"fact": "attestation.confidence"},
                    "right": {"fact": "contract.min_diagnosis_confidence"},
                }
            },
        ]
    }
    assert _evaluate_gate_expression(expression, facts) is True


def test_load_gate_rules_rejects_invalid_schema(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".providence" / "skills" / "sdd-correct"
    rules_dir.mkdir(parents=True)
    (rules_dir / "gate-rules.yaml").write_text(
        "rules:\n  - id: broken\n    priority: 5\n    decision: allow\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing required fields"):
        _load_gate_rules(project_root=tmp_path, skill=_make_skill())


# ---------------------------------------------------------------------------
# CorrectHandler.pre_run
# ---------------------------------------------------------------------------


def _make_learning(active_rules: list | None = None) -> MagicMock:
    m = MagicMock()
    m.list_active_rules.return_value = active_rules or []
    return m


def _make_skill(name: str = "sdd-correct") -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        cli_fallback=["providence governance validate"],
        config={"gate_rules_file": ".providence/skills/sdd-correct/gate-rules.yaml"},
    )


def test_load_gate_rules_reads_yaml_file(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".providence" / "skills" / "sdd-correct"
    rules_dir.mkdir(parents=True)
    (rules_dir / "gate-rules.yaml").write_text(
        "rules:\n"
        "  - id: custom\n"
        "    priority: 5\n"
        "    when:\n"
        "      fact: always\n"
        "    decision: allow\n"
        "    reason_code: ok\n"
        "    next_action: apply-correction\n"
        "    requires_human_review: false\n"
        "    escalate_to_human: false\n",
        encoding="utf-8",
    )
    rules = _load_gate_rules(project_root=tmp_path, skill=_make_skill())
    assert rules[0]["id"] == "custom"


def test_load_gate_rules_falls_back_when_file_missing(tmp_path: Path) -> None:
    rules = _load_gate_rules(project_root=tmp_path, skill=_make_skill())
    assert rules[0]["id"] == "freeze_mode_active"


def test_pre_run_denies_when_gate_rule_schema_invalid(tmp_path: Path) -> None:
    handler = CorrectHandler()
    rules_dir = tmp_path / ".providence" / "skills" / "sdd-correct"
    rules_dir.mkdir(parents=True)
    (rules_dir / "gate-rules.yaml").write_text(
        "rules:\n"
        "  - id: broken\n"
        "    priority: 5\n"
        "    when:\n"
        "      unknown: true\n"
        "    decision: allow\n"
        "    reason_code: ok\n"
        "    next_action: apply-correction\n"
        "    requires_human_review: false\n"
        "    escalate_to_human: false\n",
        encoding="utf-8",
    )
    ctx = _ctx(evidence=["e"], confidence=0.9, allowed=["safe/"], planned=["safe/"])
    ctx["_project_root"] = tmp_path
    learning = _make_learning()
    outcome = handler.pre_run(
        ctx,
        learning=learning,
        skill=_make_skill(),
        profile="default",
        footer_fn=lambda d, g: "",
    )
    assert outcome.early_result is not None
    assert outcome.early_result.policy_result == "denied"
    assert outcome.early_result.reason == "gate.rules.invalid"
    assert outcome.artifacts["gate_rule_error"].startswith("unsupported gate operator")
    learning.append_failure.assert_called_once()


def test_pre_run_returns_gate_decision_artifact() -> None:
    handler = CorrectHandler()
    ctx = _ctx(evidence=["e"], confidence=0.9, allowed=["safe/"], planned=["safe/"])
    outcome = handler.pre_run(
        ctx,
        learning=_make_learning(),
        skill=_make_skill(),
        profile="default",
        footer_fn=lambda d, g: "",
    )
    assert "gate_decision" in outcome.artifacts
    assert outcome.artifacts["gate_decision"]["decision"] == "allow"
    assert outcome.early_result is None


def test_pre_run_escalates_on_inconclusive_diagnosis() -> None:
    handler = CorrectHandler()
    ctx = _ctx(evidence=["e"], confidence=0.2)
    learning = _make_learning()
    outcome = handler.pre_run(
        ctx,
        learning=learning,
        skill=_make_skill(),
        profile="default",
        footer_fn=lambda d, g: "",
    )
    assert outcome.early_result is not None
    assert outcome.early_result.policy_result == "escalated"
    learning.append_failure.assert_called_once()


def test_pre_run_denies_scope_violation() -> None:
    handler = CorrectHandler()
    ctx = _ctx(evidence=["e"], confidence=0.9, allowed=["safe/"], planned=["unsafe/"])
    learning = _make_learning()
    outcome = handler.pre_run(
        ctx,
        learning=learning,
        skill=_make_skill(),
        profile="default",
        footer_fn=lambda d, g: "",
    )
    assert outcome.early_result is not None
    assert outcome.early_result.policy_result == "denied"
    learning.append_failure.assert_called_once()


def test_pre_run_uses_footer_fn_for_early_result() -> None:
    handler = CorrectHandler()
    ctx = _ctx(evidence=[], confidence=0.9)
    calls: list[tuple[str, str]] = []

    def footer(drift: str, governance: str) -> str:
        calls.append((drift, governance))
        return "FOOTER"

    outcome = handler.pre_run(
        ctx,
        learning=_make_learning(),
        skill=_make_skill(),
        profile="default",
        footer_fn=footer,
    )
    assert outcome.early_result is not None
    assert outcome.early_result.governance_footer == "FOOTER"
    assert calls == [("fallback_cli", "fail")]


# ---------------------------------------------------------------------------
# CorrectHandler.post_run
# ---------------------------------------------------------------------------


def test_post_run_appends_failure_and_returns_candidates() -> None:
    handler = CorrectHandler()
    ctx = _ctx(evidence=["e"], confidence=0.9)
    learning = _make_learning()
    candidate = SimpleNamespace(pattern="h|r")
    learning.generate_candidates_from_ledger.return_value = [candidate]

    result = handler.post_run(ctx, learning=learning, exit_code=0, artifacts={})
    learning.append_failure.assert_called_once()
    assert result["rule_candidates"] == [{"pattern": "h|r"}]


def test_post_run_marks_regression_when_exit_code_nonzero() -> None:
    handler = CorrectHandler()
    ctx = _ctx(evidence=["e"], confidence=0.9)
    learning = _make_learning()
    learning.generate_candidates_from_ledger.return_value = []

    handler.post_run(ctx, learning=learning, exit_code=1, artifacts={})
    call_args = learning.append_failure.call_args[0][0]
    assert call_args.regression is True


def test_post_run_returns_empty_when_diagnosis_report_is_not_dict() -> None:
    handler = CorrectHandler()
    result = handler.post_run(
        {"diagnosis_report": "bad_value"},
        learning=_make_learning(),
        exit_code=0,
        artifacts={},
    )
    assert result == {}
