"""Execution contract, diagnosis, and convergence report builders."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from .._constants import (
    ATTESTATION_TTL_MINUTES_DEFAULT,
    MIN_DIAGNOSIS_CONFIDENCE_DEFAULT,
)


def _build_execution_contract(context: dict[str, Any]) -> dict[str, Any]:
    contract = context.get("execution_contract", {})
    if not isinstance(contract, dict):
        contract = {}
    defaults: dict[str, Any] = {
        "schema_version": "1.0",
        "origin": "skill_executor",
        "task_id": f"task-{uuid4().hex[:12]}",
        "task_type": "unspecified",
        "goal": "unspecified",
        "allowed_paths": [],
        "forbidden_paths": [],
        "allowed_tools": [],
        "validation_set": [],
        "rollback_hint": "manual_rollback",
        "escalation_policy": "human_on_inconclusive_diagnosis",
        "requires_diagnosis": True,
        "min_diagnosis_confidence": MIN_DIAGNOSIS_CONFIDENCE_DEFAULT,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (
            datetime.now(timezone.utc)
            + timedelta(minutes=ATTESTATION_TTL_MINUTES_DEFAULT)
        ).isoformat(),
    }
    return {**defaults, **contract}


def _build_diagnosis_report(context: dict[str, Any]) -> dict[str, Any]:
    report = context.get("diagnosis_report", {})
    if not isinstance(report, dict):
        report = {}
    defaults: dict[str, Any] = {
        "hypothesis": "unknown",
        "root_cause": "inconclusive",
        "evidence_refs": [],
        "confidence": 0.0,
        "affected_invariants": [],
    }
    return {**defaults, **report}


def _build_diagnosis_attestation(context: dict[str, Any]) -> dict[str, Any]:
    contract = _build_execution_contract(context)
    report = _build_diagnosis_report(context)
    issued_at = datetime.now(timezone.utc)
    defaults = {
        "task_id": contract.get("task_id", ""),
        "hypothesis": report.get("hypothesis", "unknown"),
        "root_cause": report.get("root_cause", "inconclusive"),
        "evidence_refs": report.get("evidence_refs", []),
        "confidence": report.get("confidence", 0.0),
        "affected_invariants": report.get("affected_invariants", []),
        "issued_at": issued_at.isoformat(),
        "expires_at": (
            issued_at + timedelta(minutes=ATTESTATION_TTL_MINUTES_DEFAULT)
        ).isoformat(),
    }
    override = context.get("diagnosis_attestation", {})
    if isinstance(override, dict):
        return {**defaults, **override}
    return defaults


def _build_convergence_delta_report(context: dict[str, Any]) -> dict[str, Any]:
    report = context.get("convergence_delta_report", {})
    if not isinstance(report, dict):
        report = {}
    defaults: dict[str, Any] = {
        "alignment_score": 0.0,
        "residual_violations": [],
        "next_targets": [],
    }
    return {**defaults, **report}
