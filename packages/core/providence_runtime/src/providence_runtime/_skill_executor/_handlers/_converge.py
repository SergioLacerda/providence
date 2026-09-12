"""ConvergeHandler — convergence delta and freeze-mode artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .._base import Handler
from .._constants import (
    CONVERGENCE_FREEZE_ALIGNMENT_THRESHOLD,
    REASON_CODE_CONVERGENCE_FREEZE,
)
from .._context_builders import _build_convergence_delta_report


class ConvergeHandler(Handler):
    """Finalize corrective work and compute convergence/freeze artifacts.

    Example:
        Low alignment or too many residual violations enables
        `freeze_mode_state` and forces upstream pipeline escalation.
    """

    def post_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        exit_code: int,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        delta_report = _build_convergence_delta_report(context)
        freeze_mode = {
            "enabled": False,
            "trigger_reason": "",
            "since": "",
            "exit_criteria": "alignment_score>=0.80 and residual_violations<3",
        }
        alignment_score = float(delta_report.get("alignment_score", 0.0))
        residual = delta_report.get("residual_violations", [])
        if alignment_score < CONVERGENCE_FREEZE_ALIGNMENT_THRESHOLD or (
            isinstance(residual, list) and len(residual) >= 3
        ):
            freeze_mode = {
                "enabled": True,
                "trigger_reason": REASON_CODE_CONVERGENCE_FREEZE,
                "since": datetime.now(timezone.utc).isoformat(),
                "exit_criteria": "alignment_score>=0.80 and residual_violations<3",
            }
        new_artifacts: dict[str, Any] = {
            "convergence_delta_report": delta_report,
            "freeze_mode_state": freeze_mode,
        }
        decision = context.get("rule_decision")
        if isinstance(decision, dict):
            new_artifacts["rule_decision"] = learning.decide_rule(
                candidate_id=str(decision.get("candidate_id", "")),
                approved=bool(decision.get("approved", False)),
                reviewer=str(decision.get("reviewer", "human")),
                rationale=str(decision.get("rationale", "")),
                ttl_days=int(decision.get("ttl_days", 30)),
            )
        impact = context.get("rule_impact")
        if isinstance(impact, dict):
            learning.record_rule_impact(
                rule_id=str(impact.get("rule_id", "")),
                rework_delta=float(impact.get("rework_delta", 0.0)),
                false_block_rate=float(impact.get("false_block_rate", 0.0)),
                escalation_delta=float(impact.get("escalation_delta", 0.0)),
                rollback_flag=bool(impact.get("rollback_flag", False)),
            )
            new_artifacts["rule_impact"] = impact
        return new_artifacts
