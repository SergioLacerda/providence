"""Skill runtime contracts and execution engine.

This module is the canonical authority for capability-oriented execution:
CLI adapters should delegate here and avoid embedding domain execution logic.

Public contracts (SkillRunResult, AwakeningProfile, errors, validate_*) are
re-exported from providence_skills for consumers that do not need the full engine.
"""

from __future__ import annotations

from providence_skills import (
    AwakeningProfile,
    SkillContractError,
    SkillRunResult,
    UnauthorizedSkillError,
    format_governance_footer,
    validate_awakening_profile,
    validate_skill_definition,
)

from .._skill_contracts import (
    TOKEN_BUDGET_LOW,
    TOKEN_BUDGET_MEDIUM,
    RiskScore,
    SkillDefinition,
    SkillStatus,
)
from .._skill_executor import (
    AskHandler,
    ConvergeHandler,
    CorrectHandler,
    DiagnoseHandler,
    PreRunOutcome,
    SkillExecutor,
    _build_convergence_delta_report,
    _build_diagnosis_attestation,
    _build_diagnosis_report,
    _build_execution_contract,
    _evaluate_correction_gate,
    _get_skill_handler,
)
from .._skill_registry import SkillRegistry
from ._engine import SkillEngine
from ._registry_data import _REGISTRY

__all__ = [
    "_REGISTRY",
    "AskHandler",
    "AwakeningProfile",
    "ConvergeHandler",
    "CorrectHandler",
    "DiagnoseHandler",
    "PreRunOutcome",
    "RiskScore",
    "SkillContractError",
    "SkillDefinition",
    "SkillEngine",
    "SkillExecutor",
    "SkillRegistry",
    "SkillRunResult",
    "SkillStatus",
    "TOKEN_BUDGET_LOW",
    "TOKEN_BUDGET_MEDIUM",
    "UnauthorizedSkillError",
    "_build_convergence_delta_report",
    "_build_diagnosis_attestation",
    "_build_diagnosis_report",
    "_build_execution_contract",
    "_evaluate_correction_gate",
    "_get_skill_handler",
    "format_governance_footer",
    "validate_awakening_profile",
    "validate_skill_definition",
]
