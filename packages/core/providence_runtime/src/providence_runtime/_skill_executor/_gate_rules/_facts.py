"""Fact resolution and correction gate fact-building helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .._constants import MIN_DIAGNOSIS_CONFIDENCE_DEFAULT
from .._context_builders import _build_execution_contract


def _resolve_fact_value(facts: dict[str, Any], path: str) -> Any:
    current: Any = facts
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def _resolve_gate_operand(operand: Any, facts: dict[str, Any]) -> Any:
    if isinstance(operand, dict) and set(operand) == {"fact"}:
        fact_path = operand.get("fact")
        if not isinstance(fact_path, str) or not fact_path.strip():
            raise ValueError("gate operand fact reference must be a non-empty string")
        return _resolve_fact_value(facts, fact_path)
    return operand


def _build_correction_gate_facts(
    context: dict[str, Any],
    *,
    active_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    contract = _build_execution_contract(context)
    freeze_mode_state = context.get("freeze_mode_state", {})
    attestation = context.get("diagnosis_attestation", {})
    if not isinstance(attestation, dict):
        attestation = {}
    contract_expires_at = str(contract.get("expires_at", ""))
    contract_invalid = False
    contract_expired = False
    if contract_expires_at:
        try:
            contract_expires_dt = datetime.fromisoformat(
                contract_expires_at.replace("Z", "+00:00")
            )
            contract_expired = contract_expires_dt <= datetime.now(timezone.utc)
        except ValueError:
            contract_invalid = True

    attestation_invalid = False
    attestation_expired = False
    expires_at = str(attestation.get("expires_at", ""))
    if expires_at:
        try:
            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            attestation_expired = expires_dt <= datetime.now(timezone.utc)
        except ValueError:
            attestation_invalid = True

    evidence = attestation.get("evidence_refs", [])
    confidence = attestation.get("confidence", 0.0)
    allowed_paths = contract.get("allowed_paths", [])
    planned_paths = context.get("planned_paths", [])
    min_conf = float(
        contract.get("min_diagnosis_confidence", MIN_DIAGNOSIS_CONFIDENCE_DEFAULT)
    )
    pattern = (
        f"{attestation.get('hypothesis', 'unknown')}|"
        f"{attestation.get('root_cause', 'unknown')}"
    )
    return {
        "freeze_mode": {
            "enabled": isinstance(freeze_mode_state, dict)
            and bool(freeze_mode_state.get("enabled"))
        },
        "attestation": {
            "present": bool(attestation),
            "task_id": str(attestation.get("task_id", "")),
            "invalid": attestation_invalid,
            "expired": attestation_expired,
            "has_evidence": isinstance(evidence, list) and bool(evidence),
            "confidence": float(confidence)
            if isinstance(confidence, int | float)
            else float("-inf"),
            "hypothesis": str(attestation.get("hypothesis", "unknown")),
            "root_cause": str(attestation.get("root_cause", "unknown")),
        },
        "contract": {
            "task_id": str(contract.get("task_id", "")),
            "invalid": contract_invalid,
            "expired": contract_expired,
            "allowed_paths": list(allowed_paths)
            if isinstance(allowed_paths, list)
            else [],
            "allowed_paths_present": isinstance(allowed_paths, list)
            and bool(allowed_paths),
            "min_diagnosis_confidence": min_conf,
        },
        "planned_paths": list(planned_paths) if isinstance(planned_paths, list) else [],
        "scope_violation": isinstance(planned_paths, list)
        and bool(planned_paths)
        and any(path not in allowed_paths for path in planned_paths),
        "active_rule_patterns": [
            str(rule.get("pattern", ""))
            for rule in active_rules
            if isinstance(rule, dict) and str(rule.get("pattern", "")).strip()
        ],
        "current_pattern": pattern,
        "always": True,
    }
