"""Tests for providence_runtime._skill_executor._gate_rules._normalization.

Covers the gate expression/rule normalization helpers: happy paths for every
supported operator plus the validation errors raised for malformed payloads.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from providence_runtime._skill_executor._gate_rules._normalization import (
    _load_gate_rules,
    _normalize_collection_operator,
    _normalize_comparison_operator,
    _normalize_contains_operator,
    _normalize_fact_operator,
    _normalize_gate_expression,
    _normalize_gate_rule,
    _normalize_in_operator,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _normalize_fact_operator
# ---------------------------------------------------------------------------


def test_normalize_fact_operator_accepts_path() -> None:
    assert _normalize_fact_operator("attestation.present") == {
        "fact": "attestation.present"
    }


@pytest.mark.parametrize("payload", ["", "   ", 123, None, ["a"]])
def test_normalize_fact_operator_rejects_invalid_payload(payload: object) -> None:
    with pytest.raises(ValueError, match="non-empty string path"):
        _normalize_fact_operator(payload)


# ---------------------------------------------------------------------------
# _normalize_collection_operator (all / any)
# ---------------------------------------------------------------------------


def test_normalize_collection_operator_normalizes_items() -> None:
    result = _normalize_collection_operator("all", [{"fact": "a"}, {"fact": "b"}])
    assert result == {"all": [{"fact": "a"}, {"fact": "b"}]}


@pytest.mark.parametrize("payload", [[], "not-a-list", None, {}])
def test_normalize_collection_operator_rejects_invalid_payload(payload: object) -> None:
    with pytest.raises(ValueError, match="requires a non-empty list"):
        _normalize_collection_operator("any", payload)


# ---------------------------------------------------------------------------
# _normalize_comparison_operator (eq / ne / lt / lte / gt / gte)
# ---------------------------------------------------------------------------


def test_normalize_comparison_operator_normalizes_left_right() -> None:
    payload = {"left": {"fact": "a"}, "right": {"fact": "b"}}
    result = _normalize_comparison_operator("eq", payload)
    assert result == {"eq": {"left": {"fact": "a"}, "right": {"fact": "b"}}}


@pytest.mark.parametrize(
    "payload",
    [
        {"left": 1},
        {"left": 1, "right": 2, "extra": 3},
        "not-a-dict",
        None,
        [],
    ],
)
def test_normalize_comparison_operator_rejects_invalid_payload(payload: object) -> None:
    with pytest.raises(ValueError, match="requires left/right operands"):
        _normalize_comparison_operator("gte", payload)


# ---------------------------------------------------------------------------
# _normalize_in_operator
# ---------------------------------------------------------------------------


def test_normalize_in_operator_normalizes_item_items() -> None:
    payload = {"item": {"fact": "a"}, "items": [1, 2, 3]}
    assert _normalize_in_operator(payload) == {
        "in": {"item": {"fact": "a"}, "items": [1, 2, 3]}
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"item": "a"},
        {"item": "a", "items": [], "extra": True},
        "not-a-dict",
        None,
    ],
)
def test_normalize_in_operator_rejects_invalid_payload(payload: object) -> None:
    with pytest.raises(ValueError, match="requires item/items operands"):
        _normalize_in_operator(payload)


# ---------------------------------------------------------------------------
# _normalize_contains_operator
# ---------------------------------------------------------------------------


def test_normalize_contains_operator_normalizes_collection_item() -> None:
    payload = {"collection": {"fact": "a"}, "item": "x"}
    assert _normalize_contains_operator(payload) == {
        "contains": {"collection": {"fact": "a"}, "item": "x"}
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"collection": []},
        {"collection": [], "item": "x", "extra": True},
        "not-a-dict",
        None,
    ],
)
def test_normalize_contains_operator_rejects_invalid_payload(payload: object) -> None:
    with pytest.raises(ValueError, match="requires collection/item operands"):
        _normalize_contains_operator(payload)


# ---------------------------------------------------------------------------
# _normalize_gate_expression — dispatch + structural validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("expression", [{}, {"a": 1, "b": 2}, "not-a-dict", None, []])
def test_normalize_gate_expression_rejects_non_single_key_mapping(
    expression: object,
) -> None:
    with pytest.raises(ValueError, match="single-key mapping"):
        _normalize_gate_expression(expression)


def test_normalize_gate_expression_rejects_unsupported_operator() -> None:
    with pytest.raises(ValueError, match="unsupported gate operator: nope"):
        _normalize_gate_expression({"nope": "value"})


def test_normalize_gate_expression_fact() -> None:
    assert _normalize_gate_expression({"fact": "x"}) == {"fact": "x"}


@pytest.mark.parametrize("op_name", ["all", "any"])
def test_normalize_gate_expression_collection_ops(op_name: str) -> None:
    expression = {op_name: [{"fact": "a"}]}
    assert _normalize_gate_expression(expression) == {op_name: [{"fact": "a"}]}


def test_normalize_gate_expression_not() -> None:
    assert _normalize_gate_expression({"not": {"fact": "x"}}) == {"not": {"fact": "x"}}


@pytest.mark.parametrize("op_name", ["eq", "ne", "lt", "lte", "gt", "gte"])
def test_normalize_gate_expression_comparison_ops(op_name: str) -> None:
    expression = {op_name: {"left": {"fact": "a"}, "right": {"fact": "b"}}}
    assert _normalize_gate_expression(expression) == {
        op_name: {"left": {"fact": "a"}, "right": {"fact": "b"}}
    }


def test_normalize_gate_expression_in() -> None:
    expression = {"in": {"item": {"fact": "a"}, "items": [1, 2]}}
    assert _normalize_gate_expression(expression) == {
        "in": {"item": {"fact": "a"}, "items": [1, 2]}
    }


def test_normalize_gate_expression_contains() -> None:
    expression = {"contains": {"collection": {"fact": "a"}, "item": "x"}}
    assert _normalize_gate_expression(expression) == {
        "contains": {"collection": {"fact": "a"}, "item": "x"}
    }


# ---------------------------------------------------------------------------
# _normalize_gate_rule
# ---------------------------------------------------------------------------


def _valid_rule(**overrides: object) -> dict:
    rule = {
        "id": "custom",
        "priority": 5,
        "when": {"fact": "always"},
        "decision": "allow",
        "reason_code": "ok",
        "next_action": "apply-correction",
        "requires_human_review": False,
        "escalate_to_human": False,
    }
    rule.update(overrides)
    return rule


@pytest.mark.parametrize("rule", ["not-a-dict", None, []])
def test_normalize_gate_rule_rejects_non_mapping(rule: object) -> None:
    with pytest.raises(ValueError, match="must be a mapping"):
        _normalize_gate_rule(rule)


def test_normalize_gate_rule_rejects_unsupported_decision() -> None:
    with pytest.raises(ValueError, match="unsupported gate decision: maybe"):
        _normalize_gate_rule(_valid_rule(decision="maybe"))


def test_normalize_gate_rule_normalizes_valid_rule() -> None:
    result = _normalize_gate_rule(_valid_rule())
    assert result == {
        "id": "custom",
        "priority": 5,
        "when": {"fact": "always"},
        "decision": "allow",
        "reason_code": "ok",
        "next_action": "apply-correction",
        "requires_human_review": False,
        "escalate_to_human": False,
    }


# ---------------------------------------------------------------------------
# _load_gate_rules — empty rules list
# ---------------------------------------------------------------------------


def _make_skill(gate_rules_file: str) -> object:
    from types import SimpleNamespace

    return SimpleNamespace(
        name="sdd-correct", config={"gate_rules_file": gate_rules_file}
    )


def test_load_gate_rules_falls_back_when_gate_rules_file_unset(tmp_path: Path) -> None:
    skill = _make_skill("")
    rules = _load_gate_rules(project_root=tmp_path, skill=skill)
    assert rules[0]["id"] == "freeze_mode_active"


def test_load_gate_rules_rejects_empty_rules_list(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".providence" / "skills" / "sdd-correct"
    rules_dir.mkdir(parents=True)
    (rules_dir / "gate-rules.yaml").write_text("rules: []\n", encoding="utf-8")

    skill = _make_skill(".providence/skills/sdd-correct/gate-rules.yaml")
    with pytest.raises(ValueError, match="non-empty 'rules' list"):
        _load_gate_rules(project_root=tmp_path, skill=skill)
