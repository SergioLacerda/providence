"""CorrectHandler — correction gate evaluation before governed fixes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providence_skills import SkillRunResult

from ...learning import FailureLedgerEntry
from .._base import Handler, PreRunOutcome
from .._constants import REASON_CODE_GATE_RULES_INVALID, _FooterFn
from .._gate_rules import _evaluate_correction_gate, _load_gate_rules


class CorrectHandler(Handler):
    """Evaluate correction gates before any governed fix is attempted.

    Example:
        Deny a correction when `planned_paths` escape `allowed_paths`, or allow
        the correction and record downstream rule-candidate evidence.
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
        project_root_raw = context.get("_project_root", Path.cwd())
        project_root = Path(project_root_raw)
        try:
            gate_rules = _load_gate_rules(project_root=project_root, skill=skill)
        except ValueError as exc:
            gate: dict[str, Any] = {
                "decision": "deny",
                "reason_code": REASON_CODE_GATE_RULES_INVALID,
                "next_action": f"fix-gate-rules:{exc}",
                "requires_human_review": True,
                "escalate_to_human": True,
            }
            artifacts: dict[str, Any] = {
                "gate_decision": gate,
                "gate_rule_error": str(exc),
            }
            learning.append_failure(
                FailureLedgerEntry(
                    symptom="correction_gate_invalid",
                    root_cause=REASON_CODE_GATE_RULES_INVALID,
                    fix="fix_gate_rules_schema",
                    validation=str(exc),
                    regression=False,
                    tags=["gate", "correct", "invalid-schema"],
                    evidence_refs=[],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            early = SkillRunResult(
                state="error",
                profile=profile,
                skill=skill.name,
                policy_result="denied",
                reason=REASON_CODE_GATE_RULES_INVALID,
                exit_code=1,
                governance_footer=footer_fn("fallback_cli", "fail"),
                fallback=list(skill.cli_fallback),
                command_results=[],
                artifacts=artifacts,
            )
            return PreRunOutcome(artifacts=artifacts, early_result=early)
        gate = _evaluate_correction_gate(
            context,
            active_rules=learning.list_active_rules(),
            gate_rules=gate_rules,
        )
        artifacts = {"gate_decision": gate}
        if gate["decision"] != "allow":
            diag_report = context.get("diagnosis_report", {})
            entry = FailureLedgerEntry(
                symptom="correction_blocked",
                root_cause=gate["reason_code"],
                fix="escalate_or_re_diagnose",
                validation=gate["next_action"],
                regression=False,
                tags=["gate", "correct"],
                evidence_refs=list(diag_report.get("evidence_refs", []))
                if isinstance(diag_report, dict)
                else [],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            learning.append_failure(entry)
            early = SkillRunResult(
                state="error",
                profile=profile,
                skill=skill.name,
                policy_result="escalated"
                if gate["decision"] == "escalate"
                else "denied",
                reason=gate["reason_code"],
                exit_code=1,
                governance_footer=footer_fn("fallback_cli", "fail"),
                fallback=list(skill.cli_fallback),
                command_results=[],
                artifacts=artifacts,
            )
            return PreRunOutcome(artifacts=artifacts, early_result=early)
        return PreRunOutcome(artifacts=artifacts)

    def post_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        exit_code: int,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        diag = context.get("diagnosis_report", {})
        if not isinstance(diag, dict):
            return {}
        learning.append_failure(
            FailureLedgerEntry(
                symptom=str(diag.get("hypothesis", "unknown")),
                root_cause=str(diag.get("root_cause", "unknown")),
                fix="sdd-correct",
                validation="postcheck",
                regression=exit_code != 0,
                tags=["correct", "executed" if exit_code == 0 else "failed"],
                evidence_refs=[
                    ref for ref in diag.get("evidence_refs", []) if isinstance(ref, str)
                ],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return {
            "rule_candidates": [
                candidate.__dict__
                for candidate in learning.generate_candidates_from_ledger()
            ]
        }
