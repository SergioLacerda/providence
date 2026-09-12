"""Handler factory and pipeline composition helpers."""

from __future__ import annotations

from typing import Any

from .._base import ContextCarrier
from ._ask import AskHandler
from ._compress_context import CompressContextHandler
from ._converge import ConvergeHandler
from ._correct import CorrectHandler
from ._diagnose import DiagnoseHandler
from ._pipeline import PipelineHandler
from ._review_architecture import ReviewArchitectureHandler
from ._stabilize import StabilizeHandler

# ---------------------------------------------------------------------------
# Handler factory
# ---------------------------------------------------------------------------


def _get_skill_handler(name: str) -> Any:
    if not name.startswith("sdd-"):
        return None
    suffix = name[4:]
    class_name = suffix.replace("-", " ").title().replace(" ", "") + "Handler"
    cls = globals().get(class_name)
    if cls is None:
        return None
    return cls()


# ---------------------------------------------------------------------------
# Pipeline composition helpers
# ---------------------------------------------------------------------------


def _prepare_pipeline_stages(
    carrier: ContextCarrier, compose_config: dict[str, Any]
) -> tuple[list[str], list[str], dict[str, Any]]:
    """Resolve the stage list and any in-progress pipeline state for composition."""
    stages_raw = compose_config.get("stages", [])
    stages = [
        PipelineHandler._normalize_stage_name(stage)
        for stage in stages_raw
        if str(stage).strip()
    ]
    if not stages:
        stages = list(PipelineHandler._DEFAULT_STAGES)

    pipeline_state = carrier.get("pipeline_state", {})
    if not isinstance(pipeline_state, dict):
        pipeline_state = {}
    completed_stages: list[str] = list(pipeline_state.get("completed_stages", []))
    stage_results: dict[str, Any] = dict(pipeline_state.get("stage_results", {}))
    return stages, completed_stages, stage_results


def _classify_execution_outcome(
    *, execute: bool, exit_code: int, execution_errors: list[str]
) -> tuple[str, str, str]:
    """Derive (policy_result, reason, drift) for a completed skill run."""
    if not execute:
        return "planned", "dry-run policy planning", "none"
    policy_result = "timeout" if exit_code == 124 else "executed"
    reason = (
        "runtime execution completed"
        if exit_code == 0
        else f"execution failed: {'; '.join(execution_errors)}"
    )
    return policy_result, reason, "fallback_cli"


__all__ = [
    "AskHandler",
    "CompressContextHandler",
    "ConvergeHandler",
    "CorrectHandler",
    "DiagnoseHandler",
    "PipelineHandler",
    "ReviewArchitectureHandler",
    "StabilizeHandler",
    "_classify_execution_outcome",
    "_get_skill_handler",
    "_prepare_pipeline_stages",
]
