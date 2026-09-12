"""Correction gate expression and rule evaluation."""

from __future__ import annotations

import operator as _op
from collections.abc import Callable
from typing import Any

from ._default_rules import _default_correction_gate_rules
from ._facts import (
    _build_correction_gate_facts,
    _resolve_fact_value,
    _resolve_gate_operand,
)

_GATE_COMPARISON_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "eq": _op.eq,
    "ne": _op.ne,
    "lt": _op.lt,
    "lte": _op.le,
    "gt": _op.gt,
    "gte": _op.ge,
}


def _evaluate_comparison_expression(
    op_name: str, payload: dict[str, Any], facts: dict[str, Any]
) -> bool:
    left = _resolve_gate_operand(payload["left"], facts)
    right = _resolve_gate_operand(payload["right"], facts)
    return _GATE_COMPARISON_OPS[op_name](left, right)


def _evaluate_membership_expression(
    op_name: str, payload: dict[str, Any], facts: dict[str, Any]
) -> bool:
    item = _resolve_gate_operand(payload["item"], facts)
    collection_key = "items" if op_name == "in" else "collection"
    collection = _resolve_gate_operand(payload[collection_key], facts)
    return item in collection


def _evaluate_gate_expression(
    expression: dict[str, Any], facts: dict[str, Any]
) -> bool:
    op_name, payload = next(iter(expression.items()))
    if op_name == "fact":
        return bool(_resolve_fact_value(facts, payload))
    if op_name == "all":
        return all(_evaluate_gate_expression(item, facts) for item in payload)
    if op_name == "any":
        return any(_evaluate_gate_expression(item, facts) for item in payload)
    if op_name == "not":
        return not _evaluate_gate_expression(payload, facts)
    if op_name in _GATE_COMPARISON_OPS:
        return _evaluate_comparison_expression(op_name, payload, facts)
    return _evaluate_membership_expression(op_name, payload, facts)


def _evaluate_correction_gate(
    context: dict[str, Any],
    *,
    active_rules: list[dict[str, Any]],
    gate_rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rules = gate_rules or _default_correction_gate_rules()
    facts = _build_correction_gate_facts(context, active_rules=active_rules)
    for rule in sorted(rules, key=lambda item: int(item.get("priority", 9999))):
        if not _evaluate_gate_expression(rule["when"], facts):
            continue
        return {
            "decision": str(rule.get("decision", "deny")),
            "reason_code": str(rule.get("reason_code", "contract.missing_or_invalid")),
            "next_action": str(rule.get("next_action", "human-review")),
            "requires_human_review": bool(rule.get("requires_human_review", True)),
            "escalate_to_human": bool(rule.get("escalate_to_human", True)),
            "rule_id": str(rule.get("id", "")),
        }
    return _default_correction_gate_rules()[-1].copy()
