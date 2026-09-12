"""PipelineHandler — validate and compose the governed pipeline flow."""

from __future__ import annotations

from typing import Any

from providence_skills import SkillRunResult

from .._base import Handler, PreRunOutcome
from .._constants import _FooterFn


class PipelineHandler(Handler):
    """Validate and compose the governed ask→diagnose→correct→converge flow.

    Example:
        The handler requests composition when `sdd-pipeline` is invoked and the
        executor runs the configured stages with shared `ContextCarrier` state.
    """

    _DEFAULT_STAGES = [
        "sdd-ask",
        "sdd-diagnose",
        "sdd-correct",
        "sdd-converge",
    ]

    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        del learning, profile, footer_fn
        skill_config = getattr(skill, "config", {})
        pipeline_config = (
            skill_config.get("pipeline", {}) if isinstance(skill_config, dict) else {}
        )
        stages = context.get(
            "pipeline_stages",
            pipeline_config.get("stages", self._DEFAULT_STAGES),
        )
        if not isinstance(stages, list) or not stages:
            stages = list(self._DEFAULT_STAGES)
        normalized = [self._normalize_stage_name(stage) for stage in stages]
        invalid = [stage for stage in normalized if stage not in self._DEFAULT_STAGES]
        if invalid:
            early = SkillRunResult(
                state="error",
                profile="default",
                skill=skill.name,
                policy_result="invalid_pipeline",
                reason=f"invalid_pipeline_stages:{','.join(invalid)}",
                exit_code=1,
                governance_footer="",
                artifacts={},
            )
            return PreRunOutcome(early_result=early)
        pipeline_state = {
            "stages": normalized,
            "completed_stages": [],
            "stage_results": {},
            "escalation_triggered": False,
            "escalation_reason": "",
        }
        decision_gates = {
            "diagnose_to_correct_min_confidence": float(
                context.get(
                    "pipeline_min_diagnosis_confidence",
                    pipeline_config.get("decision_gates", {}).get(
                        "diagnose_to_correct_min_confidence", 0.70
                    ),
                )
            )
        }
        return PreRunOutcome(
            artifacts={"pipeline_state": pipeline_state},
            compose_config={"stages": normalized, "decision_gates": decision_gates},
        )

    @classmethod
    def _normalize_stage_name(cls, value: Any) -> str:
        stage = str(value)
        return stage if stage.startswith("sdd-") else f"sdd-{stage}"
