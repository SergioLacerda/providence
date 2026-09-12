"""TypedDict result shapes and builders for the wizard's phase pipelines."""

from pathlib import Path
from typing import Any, TypedDict


class Phase1RunResult(TypedDict, total=False):
    """Phase1RunResult."""

    success: bool
    error: str
    mandate_count: int
    guideline_count: int
    mandate_spec_output: str
    output_path: str
    mandates: list[dict[str, Any]]
    guidelines: list[dict[str, Any]]


class ParsedItems(TypedDict):
    """ParsedItems."""

    mandates: list[dict[str, Any]]
    guidelines: list[dict[str, Any]]


class Phase3RunResult(TypedDict, total=False):
    """Phase3RunResult."""

    success: bool
    error: str
    output_path: str
    language: str
    files: list[str]
    mandates: int
    guidelines: int


class Phase456RunResult(TypedDict, total=False):
    """Phase456RunResult."""

    success: bool
    phase: str
    output_path: str
    mandates: int
    guidelines: int
    categories: list[str]
    errors: list[str]
    validation: dict[str, str]


class ValidationDetail(TypedDict):
    """ValidationDetail."""

    valid: bool
    checks: dict[str, str]
    errors: list[str]


class FinalTemplateConsolidationResult(TypedDict):
    """FinalTemplateConsolidationResult."""

    success: bool
    source_dir: str
    target_dir: str
    moved_items: int
    error: str


class Phase1GenerateResult(TypedDict):
    """Phase1GenerateResult."""

    success: bool
    config_path: str
    output_path: str
    language: str
    enforcement_mode: str
    error: str


class Phase2StageResult(TypedDict):
    """Phase2StageResult."""

    success: bool
    phase1_path: str
    output_path: str
    copied_files: list[str]
    error: str


class InteractivePhase3CompileResult(TypedDict):
    """InteractivePhase3CompileResult."""

    success: bool
    mandates: int
    guidelines: int
    files: list[str]
    output_path: str
    seedlings_success: bool
    error: str


class InteractivePhase4GenerateResult(TypedDict):
    """InteractivePhase4GenerateResult."""

    success: bool
    mandates: int
    guidelines: int
    categories: list[str]
    consolidated: bool
    error: str


def build_interactive_phase3_result(
    *,
    success: bool,
    output_path: Path,
    mandates: int = 0,
    guidelines: int = 0,
    files: list[str] | None = None,
    seedlings_success: bool = False,
    error: str = "",
) -> InteractivePhase3CompileResult:
    """Build Interactive Phase3 Result."""
    return {
        "success": success,
        "mandates": mandates,
        "guidelines": guidelines,
        "files": files or [],
        "output_path": str(output_path),
        "seedlings_success": seedlings_success,
        "error": error,
    }


def build_interactive_phase4_result(
    *,
    success: bool,
    mandates: int = 0,
    guidelines: int = 0,
    categories: list[str] | None = None,
    consolidated: bool = False,
    error: str = "",
) -> InteractivePhase4GenerateResult:
    """Build Interactive Phase4 Result."""
    return {
        "success": success,
        "mandates": mandates,
        "guidelines": guidelines,
        "categories": categories or [],
        "consolidated": consolidated,
        "error": error,
    }
