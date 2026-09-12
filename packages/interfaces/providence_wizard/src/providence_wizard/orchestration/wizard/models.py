"""SDD Wizard v3 - 3-Phase Flow with Status-aware Governance.

Phase 1: Generate markdown templates with status fields
    Input: mandate.spec, guidelines.dsl from spec/ (with canonical resolution)
  Output: generated/client/build/phase-1-choices/

Phase 2: Manual user review & customization
  Input: generated/client/build/phase-1-choices/
  Action: User edits status values in place
  Output: generated/client/build/phase-1-choices/ (User-edited markdown templates)

Phase 3: Compile & fingerprint governance
    Input: generated/client/build/phase-2-input/ (staged user-edited markdown)
  Output: generated/client/compiled/ (Final msgpack/json artifacts)
"""

from ._model_records import Guideline, Mandate
from ._model_results import (
    FinalTemplateConsolidationResult,
    InteractivePhase3CompileResult,
    InteractivePhase4GenerateResult,
    ParsedItems,
    Phase1GenerateResult,
    Phase1RunResult,
    Phase2StageResult,
    Phase3RunResult,
    Phase456RunResult,
    ValidationDetail,
    build_interactive_phase3_result,
    build_interactive_phase4_result,
)

__all__ = [
    "FinalTemplateConsolidationResult",
    "Guideline",
    "InteractivePhase3CompileResult",
    "InteractivePhase4GenerateResult",
    "Mandate",
    "ParsedItems",
    "Phase1GenerateResult",
    "Phase1RunResult",
    "Phase2StageResult",
    "Phase3RunResult",
    "Phase456RunResult",
    "ValidationDetail",
    "build_interactive_phase3_result",
    "build_interactive_phase4_result",
]
