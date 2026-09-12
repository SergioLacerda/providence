from __future__ import annotations

from unittest.mock import MagicMock

from providence_runtime._skill_executor import (
    ConvergeHandler,
    _build_convergence_delta_report,
)


def _make_learning() -> MagicMock:
    m = MagicMock()
    m.decide_rule.return_value = {"status": "ok", "rule_id": "rr-1"}
    return m


# ---------------------------------------------------------------------------
# _build_convergence_delta_report
# ---------------------------------------------------------------------------


def test_build_convergence_delta_report_defaults() -> None:
    result = _build_convergence_delta_report({})
    assert result["alignment_score"] == 0.0
    assert result["residual_violations"] == []
    assert result["next_targets"] == []


def test_build_convergence_delta_report_merges_provided() -> None:
    ctx = {
        "convergence_delta_report": {"alignment_score": 0.85, "next_targets": ["pkg/a"]}
    }
    result = _build_convergence_delta_report(ctx)
    assert result["alignment_score"] == 0.85
    assert result["next_targets"] == ["pkg/a"]
    assert result["residual_violations"] == []


def test_build_convergence_delta_report_treats_non_dict_as_empty() -> None:
    result = _build_convergence_delta_report({"convergence_delta_report": "bad"})
    assert result["alignment_score"] == 0.0


# ---------------------------------------------------------------------------
# ConvergeHandler.post_run
# ---------------------------------------------------------------------------


def test_post_run_always_returns_convergence_delta_report() -> None:
    handler = ConvergeHandler()
    result = handler.post_run({}, learning=_make_learning(), exit_code=0, artifacts={})
    assert "convergence_delta_report" in result
    assert "freeze_mode_state" in result


def test_post_run_calls_decide_rule_when_decision_provided() -> None:
    handler = ConvergeHandler()
    learning = _make_learning()
    ctx = {
        "rule_decision": {
            "candidate_id": "rc-1",
            "approved": True,
            "reviewer": "human",
            "rationale": "ok",
            "ttl_days": 30,
        }
    }
    result = handler.post_run(ctx, learning=learning, exit_code=0, artifacts={})
    learning.decide_rule.assert_called_once_with(
        candidate_id="rc-1",
        approved=True,
        reviewer="human",
        rationale="ok",
        ttl_days=30,
    )
    assert result["rule_decision"] == {"status": "ok", "rule_id": "rr-1"}


def test_post_run_skips_decide_rule_when_no_decision_in_context() -> None:
    handler = ConvergeHandler()
    learning = _make_learning()
    result = handler.post_run({}, learning=learning, exit_code=0, artifacts={})
    learning.decide_rule.assert_not_called()
    assert "rule_decision" not in result


def test_post_run_records_rule_impact_when_provided() -> None:
    handler = ConvergeHandler()
    learning = _make_learning()
    ctx = {
        "rule_impact": {
            "rule_id": "rr-1",
            "rework_delta": 0.1,
            "false_block_rate": 0.05,
            "escalation_delta": 0.0,
            "rollback_flag": False,
        }
    }
    result = handler.post_run(ctx, learning=learning, exit_code=0, artifacts={})
    learning.record_rule_impact.assert_called_once_with(
        rule_id="rr-1",
        rework_delta=0.1,
        false_block_rate=0.05,
        escalation_delta=0.0,
        rollback_flag=False,
    )
    assert result["rule_impact"] == ctx["rule_impact"]


def test_post_run_skips_impact_when_not_provided() -> None:
    handler = ConvergeHandler()
    learning = _make_learning()
    result = handler.post_run({}, learning=learning, exit_code=0, artifacts={})
    learning.record_rule_impact.assert_not_called()
    assert "rule_impact" not in result


def test_post_run_enables_freeze_mode_on_low_alignment() -> None:
    handler = ConvergeHandler()
    learning = _make_learning()
    ctx = {
        "convergence_delta_report": {"alignment_score": 0.2, "residual_violations": []}
    }
    result = handler.post_run(ctx, learning=learning, exit_code=0, artifacts={})
    assert result["freeze_mode_state"]["enabled"] is True
    assert (
        result["freeze_mode_state"]["trigger_reason"]
        == "convergence.freeze_mode_active"
    )
