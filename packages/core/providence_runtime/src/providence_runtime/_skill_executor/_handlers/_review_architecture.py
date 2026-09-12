"""ReviewArchitectureHandler — compare architecture signals against baseline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .._architecture_review import (
    _build_architecture_review,
    _load_architecture_baseline,
    _write_architecture_baseline,
)
from .._base import Handler, PreRunOutcome
from .._constants import _FooterFn
from .._context_builders import _resolve_project_root_from_context


class ReviewArchitectureHandler(Handler):
    """Compare current architecture signals against the persisted baseline.

    Example:
        A lower governance score or new violations produces remediation
        proposals and updates `.providence/runtime/architecture-baseline.json`.
    """

    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        del learning, skill, profile, footer_fn
        project_root = _resolve_project_root_from_context(context)
        baseline = _load_architecture_baseline(project_root)
        merged_context = dict(context)
        if "baseline_governance_score" not in merged_context:
            merged_context["baseline_governance_score"] = baseline.get(
                "governance_score", merged_context.get("governance_score", 0)
            )
        if "baseline_architecture_violations" not in merged_context:
            merged_context["baseline_architecture_violations"] = baseline.get(
                "architecture_violations", []
            )
        review = _build_architecture_review(merged_context)
        current_baseline = {
            "governance_score": review["governance_score"],
            "architecture_violations": list(
                merged_context.get("architecture_violations", [])
                if isinstance(merged_context.get("architecture_violations", []), list)
                else []
            ),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        baseline_path = _write_architecture_baseline(project_root, current_baseline)
        review["baseline_path"] = baseline_path.relative_to(project_root).as_posix()
        review["baseline_updated"] = True
        return PreRunOutcome(artifacts=review)
