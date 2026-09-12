"""Hardcoded default correction gate rules."""

from __future__ import annotations

from typing import Any

from .._constants import (
    REASON_CODE_CONTRACT_MISSING_OR_INVALID,
    REASON_CODE_CONVERGENCE_FREEZE,
    REASON_CODE_DIAGNOSIS_INCONCLUSIVE,
    REASON_CODE_DIAGNOSIS_MISSING,
    REASON_CODE_DIAGNOSIS_STALE,
    REASON_CODE_EVIDENCE_INSUFFICIENT,
    REASON_CODE_RULE_BLOCKED,
    REASON_CODE_SCOPE_VIOLATION,
)


def _default_correction_gate_rules() -> list[dict[str, Any]]:
    return [
        {
            "id": "freeze_mode_active",
            "priority": 10,
            "when": {"fact": "freeze_mode.enabled"},
            "decision": "deny",
            "reason_code": REASON_CODE_CONVERGENCE_FREEZE,
            "next_action": "run-converge-and-human-review",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "attestation_missing",
            "priority": 20,
            "when": {"not": {"fact": "attestation.present"}},
            "decision": "escalate",
            "reason_code": REASON_CODE_DIAGNOSIS_MISSING,
            "next_action": "providence skills run sdd-diagnose",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "attestation_task_mismatch",
            "priority": 30,
            "when": {
                "all": [
                    {"fact": "attestation.present"},
                    {
                        "not": {
                            "eq": {
                                "left": {"fact": "attestation.task_id"},
                                "right": {"fact": "contract.task_id"},
                            }
                        }
                    },
                ]
            },
            "decision": "deny",
            "reason_code": REASON_CODE_CONTRACT_MISSING_OR_INVALID,
            "next_action": "re-issue-envelope",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "contract_invalid",
            "priority": 40,
            "when": {"fact": "contract.invalid"},
            "decision": "deny",
            "reason_code": REASON_CODE_CONTRACT_MISSING_OR_INVALID,
            "next_action": "re-issue-envelope",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "contract_expired",
            "priority": 50,
            "when": {"fact": "contract.expired"},
            "decision": "deny",
            "reason_code": REASON_CODE_CONTRACT_MISSING_OR_INVALID,
            "next_action": "re-issue-envelope",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "attestation_invalid",
            "priority": 60,
            "when": {"fact": "attestation.invalid"},
            "decision": "deny",
            "reason_code": REASON_CODE_DIAGNOSIS_STALE,
            "next_action": "re-diagnose",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "attestation_expired",
            "priority": 70,
            "when": {"fact": "attestation.expired"},
            "decision": "deny",
            "reason_code": REASON_CODE_DIAGNOSIS_STALE,
            "next_action": "re-diagnose",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "evidence_missing",
            "priority": 80,
            "when": {"not": {"fact": "attestation.has_evidence"}},
            "decision": "escalate",
            "reason_code": REASON_CODE_EVIDENCE_INSUFFICIENT,
            "next_action": "re-diagnose",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "confidence_too_low",
            "priority": 90,
            "when": {
                "lt": {
                    "left": {"fact": "attestation.confidence"},
                    "right": {"fact": "contract.min_diagnosis_confidence"},
                }
            },
            "decision": "escalate",
            "reason_code": REASON_CODE_DIAGNOSIS_INCONCLUSIVE,
            "next_action": "human-review",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "allowed_paths_missing",
            "priority": 100,
            "when": {"not": {"fact": "contract.allowed_paths_present"}},
            "decision": "deny",
            "reason_code": REASON_CODE_CONTRACT_MISSING_OR_INVALID,
            "next_action": "narrow-scope",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "scope_violation",
            "priority": 110,
            "when": {"fact": "scope_violation"},
            "decision": "deny",
            "reason_code": REASON_CODE_SCOPE_VIOLATION,
            "next_action": "narrow-scope",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "matching_active_rule",
            "priority": 120,
            "when": {
                "contains": {
                    "collection": {"fact": "active_rule_patterns"},
                    "item": {"fact": "current_pattern"},
                }
            },
            "decision": "deny",
            "reason_code": REASON_CODE_RULE_BLOCKED,
            "next_action": "human-review",
            "requires_human_review": True,
            "escalate_to_human": True,
        },
        {
            "id": "default_allow",
            "priority": 1000,
            "when": {"fact": "always"},
            "decision": "allow",
            "reason_code": "ok",
            "next_action": "apply-correction",
            "requires_human_review": False,
            "escalate_to_human": False,
        },
    ]
