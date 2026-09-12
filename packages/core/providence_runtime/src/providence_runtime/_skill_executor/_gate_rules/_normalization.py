"""Gate rule loading and normalization helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

from ..._skill_contracts import SkillDefinition
from ._default_rules import _default_correction_gate_rules


def _load_gate_rules(
    *,
    project_root: Path,
    skill: SkillDefinition,
) -> list[dict[str, Any]]:
    gate_rules_file = str(skill.config.get("gate_rules_file", "")).strip()
    if not gate_rules_file or yaml is None:
        return _default_correction_gate_rules()
    rules_path = project_root / gate_rules_file
    if not rules_path.exists():
        return _default_correction_gate_rules()
    payload = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
    rules = payload.get("rules", [])
    if not isinstance(rules, list) or not rules:
        raise ValueError("gate rules file must contain a non-empty 'rules' list")
    normalized = [_normalize_gate_rule(rule) for rule in rules]
    return sorted(normalized, key=lambda rule: int(rule.get("priority", 9999)))


def _normalize_fact_operator(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, str) or not payload.strip():
        raise ValueError("gate fact operator requires a non-empty string path")
    return {"fact": payload}


def _normalize_collection_operator(op_name: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"gate operator '{op_name}' requires a non-empty list")
    return {op_name: [_normalize_gate_expression(item) for item in payload]}


def _normalize_comparison_operator(op_name: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"left", "right"}:
        raise ValueError(f"gate operator '{op_name}' requires left/right operands")
    return {op_name: {"left": payload["left"], "right": payload["right"]}}


def _normalize_in_operator(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"item", "items"}:
        raise ValueError("gate operator 'in' requires item/items operands")
    return {"in": {"item": payload["item"], "items": payload["items"]}}


def _normalize_contains_operator(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"collection", "item"}:
        raise ValueError("gate operator 'contains' requires collection/item operands")
    return {"contains": {"collection": payload["collection"], "item": payload["item"]}}


def _normalize_gate_expression(expression: Any) -> dict[str, Any]:
    if not isinstance(expression, dict) or len(expression) != 1:
        raise ValueError("gate expression must be a single-key mapping")

    op_name, payload = next(iter(expression.items()))
    supported = {
        "fact",
        "all",
        "any",
        "not",
        "eq",
        "ne",
        "lt",
        "lte",
        "gt",
        "gte",
        "in",
        "contains",
    }
    if op_name not in supported:
        raise ValueError(f"unsupported gate operator: {op_name}")

    if op_name == "fact":
        return _normalize_fact_operator(payload)
    if op_name in {"all", "any"}:
        return _normalize_collection_operator(op_name, payload)
    if op_name == "not":
        return {"not": _normalize_gate_expression(payload)}
    if op_name in {"eq", "ne", "lt", "lte", "gt", "gte"}:
        return _normalize_comparison_operator(op_name, payload)
    if op_name == "in":
        return _normalize_in_operator(payload)
    return _normalize_contains_operator(payload)


def _normalize_gate_rule(rule: Any) -> dict[str, Any]:
    if not isinstance(rule, dict):
        raise ValueError("each gate rule must be a mapping")

    required = {
        "id",
        "priority",
        "when",
        "decision",
        "reason_code",
        "next_action",
        "requires_human_review",
        "escalate_to_human",
    }
    missing = sorted(required.difference(rule))
    if missing:
        raise ValueError(f"gate rule missing required fields: {', '.join(missing)}")

    decision = str(rule.get("decision", "")).strip()
    if decision not in {"allow", "deny", "escalate"}:
        raise ValueError(f"unsupported gate decision: {decision}")

    return {
        "id": str(rule["id"]).strip(),
        "priority": int(rule["priority"]),
        "when": _normalize_gate_expression(rule["when"]),
        "decision": decision,
        "reason_code": str(rule["reason_code"]).strip(),
        "next_action": str(rule["next_action"]).strip(),
        "requires_human_review": bool(rule["requires_human_review"]),
        "escalate_to_human": bool(rule["escalate_to_human"]),
    }
