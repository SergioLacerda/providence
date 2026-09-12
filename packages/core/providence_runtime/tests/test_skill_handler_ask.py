from __future__ import annotations

from unittest.mock import MagicMock

from providence_runtime._skill_executor import AskHandler, _build_execution_contract


def _ctx(**kwargs: object) -> dict:
    return {"execution_contract": kwargs} if kwargs else {}


def test_pre_run_returns_execution_contract_artifact() -> None:
    handler = AskHandler()
    outcome = handler.pre_run(
        {}, learning=None, skill=None, profile="default", footer_fn=lambda d, g: ""
    )
    assert "execution_contract" in outcome.artifacts
    assert outcome.early_result is None


def test_pre_run_applies_defaults_when_contract_missing() -> None:
    handler = AskHandler()
    outcome = handler.pre_run(
        {}, learning=None, skill=None, profile="default", footer_fn=lambda d, g: ""
    )
    contract = outcome.artifacts["execution_contract"]
    assert contract["task_type"] == "unspecified"
    assert contract["rollback_hint"] == "manual_rollback"
    assert contract["requires_diagnosis"] is True
    assert contract["min_diagnosis_confidence"] == 0.8
    assert contract["task_id"].startswith("task-")


def test_pre_run_merges_provided_contract_over_defaults() -> None:
    handler = AskHandler()
    ctx = {"execution_contract": {"task_type": "fix", "goal": "resolve drift"}}
    outcome = handler.pre_run(
        ctx, learning=None, skill=None, profile="default", footer_fn=lambda d, g: ""
    )
    contract = outcome.artifacts["execution_contract"]
    assert contract["task_type"] == "fix"
    assert contract["goal"] == "resolve drift"
    assert contract["rollback_hint"] == "manual_rollback"


def test_pre_run_treats_non_dict_contract_as_empty() -> None:
    handler = AskHandler()
    ctx = {"execution_contract": "bad_value"}
    outcome = handler.pre_run(
        ctx, learning=None, skill=None, profile="default", footer_fn=lambda d, g: ""
    )
    assert outcome.artifacts["execution_contract"]["task_type"] == "unspecified"


def test_build_execution_contract_standalone() -> None:
    result = _build_execution_contract(
        {"execution_contract": {"allowed_paths": ["src/"]}}
    )
    assert result["allowed_paths"] == ["src/"]
    assert result["forbidden_paths"] == []


def test_build_execution_contract_default_schema_version_and_origin() -> None:
    result = _build_execution_contract({})
    assert result["schema_version"] == "1.0"
    assert result["origin"] == "skill_executor"


def test_build_execution_contract_schema_version_and_origin_overridable() -> None:
    result = _build_execution_contract(
        {"execution_contract": {"schema_version": "2.0", "origin": "custom"}}
    )
    assert result["schema_version"] == "2.0"
    assert result["origin"] == "custom"


def test_pre_run_injects_historical_context_when_learning_has_data() -> None:
    handler = AskHandler()
    learning = MagicMock()
    learning.list_failures.return_value = [{"symptom": "ask", "root_cause": "drift"}]
    learning.list_active_rules.return_value = [{"pattern": "a|b"}]

    outcome = handler.pre_run(
        {}, learning=learning, skill=None, profile="default", footer_fn=lambda d, g: ""
    )

    historical = outcome.artifacts["execution_contract"]["historical_context"]
    assert historical["recent_failures"] == [{"symptom": "ask", "root_cause": "drift"}]
    assert historical["active_rules"] == [{"pattern": "a|b"}]


def test_post_run_registers_ask_execution() -> None:
    handler = AskHandler()
    learning = MagicMock()

    result = handler.post_run(
        {},
        learning=learning,
        exit_code=0,
        artifacts={"execution_contract": {"task_type": "fix", "goal": "resolve drift"}},
    )

    assert result == {}
    learning.append_failure.assert_called_once()
    entry = learning.append_failure.call_args.args[0]
    assert entry.symptom == "fix"
    assert entry.root_cause == "resolve drift"
    assert entry.tags == ["ask", "executed"]
