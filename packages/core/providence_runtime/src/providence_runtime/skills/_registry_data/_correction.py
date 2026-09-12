"""Hardcoded fallback skill registry definitions: correction skills."""

from __future__ import annotations

from ..._skill_contracts import SkillDefinition

__all__ = ["_CORRECTION_SKILLS"]

_CORRECTION_SKILLS: dict[str, SkillDefinition] = {
    "sdd-correct": SkillDefinition(
        name="sdd-correct",
        version="1.0.0",
        category="correction",
        description="Apply minimal targeted correction to a specific governance violation.",
        when_to_use=[
            "specific violation identified by sdd-diagnose",
            "governance drift on a single item",
        ],
        outcomes=["correction_applied", "violation_resolved", "residual_violations"],
        allowed_tools=[
            "providence governance validate",
            "providence runtime status --force",
            "providence doctor run",
        ],
        cli_fallback=["providence governance validate", "providence doctor run"],
        required_permissions=["workspace-read", "workspace-write-controlled"],
        capability_id="correct",
        risk_score="medium",
        tags=["correction", "governance", "surgical"],
        triggers=[
            "governance violation",
            "fix violation",
            "correct drift",
            "specific violation",
            "targeted fix",
            "correction",
        ],
        forbidden=[
            "modify files outside declared scope",
            "apply multiple corrections in one pass",
            "skip postcheck",
        ],
        config={"gate_rules_file": ".providence/skills/sdd-correct/gate-rules.yaml"},
        fallback_to="sdd-diagnose",
        idempotent=False,
        hard_mode_invariants={
            "pre_conditions": [
                {"gate_check": "execution_gate must be allowed before proceeding"},
                {
                    "git_authorization": "git state-modifying commands require explicit user authorization in current message"
                },
            ],
            "post_conditions": [
                {"no_unauthorized_git": "M010"},
                {"gate_respected": "M015"},
            ],
            "stop_conditions": [
                "execution_gate=blocked",
                "governance_mode=hard and intake_index_mode=none",
            ],
            "forbidden_behaviors": [
                "self_authorize_git_on_task_completion",
                "proceed_when_gate_blocked",
                "treat_intake_index_mode_none_as_permission",
            ],
        },
    ),
    "sdd-converge": SkillDefinition(
        name="sdd-converge",
        version="1.0.0",
        category="convergence",
        description="Drive systemic alignment toward spec target after targeted corrections.",
        when_to_use=[
            "residual delta after sdd-correct passes",
            "pattern of drift detected",
        ],
        outcomes=[
            "alignment_score",
            "convergence_plan",
            "delta_report",
            "next_correct_targets",
        ],
        allowed_tools=[
            "providence ask",
            "providence governance validate",
            "providence runtime status --force",
            "providence doctor run",
        ],
        cli_fallback=["providence governance validate", "providence doctor run"],
        required_permissions=["workspace-read", "workspace-write-controlled"],
        capability_id="converge",
        risk_score="high",
        tags=["convergence", "governance", "strategic", "alignment"],
        escalation_policy={
            "mode": "block",
            "require_human_on": ["critical_violation", "alignment_score_below_minimum"],
        },
        triggers=[
            "residual drift",
            "pattern of violations",
            "systemic alignment",
            "converge",
            "after correction",
            "alignment score",
            "recurring violations",
        ],
        forbidden=[
            "modify files without prior sdd-correct pass",
            "skip preflight",
            "ignore scope boundaries",
            "execute without execution_contract",
        ],
        fallback_to="sdd-correct",
        idempotent=False,
        hard_mode_invariants={
            "pre_conditions": [
                {"gate_check": "execution_gate must be allowed before proceeding"},
                {
                    "git_authorization": "git state-modifying commands require explicit user authorization in current message"
                },
            ],
            "post_conditions": [
                {"no_unauthorized_git": "M010"},
                {"gate_respected": "M015"},
            ],
            "stop_conditions": [
                "execution_gate=blocked",
                "governance_mode=hard and intake_index_mode=none",
            ],
            "forbidden_behaviors": [
                "self_authorize_git_on_task_completion",
                "proceed_when_gate_blocked",
                "treat_intake_index_mode_none_as_permission",
            ],
        },
    ),
}
