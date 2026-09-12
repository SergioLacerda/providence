"""Hardcoded fallback skill registry definitions: operations skills."""

from __future__ import annotations

from ..._skill_contracts import TOKEN_BUDGET_LOW, SkillDefinition

__all__ = ["_OPERATIONS_SKILLS"]

_OPERATIONS_SKILLS: dict[str, SkillDefinition] = {
    "sdd-stabilize": SkillDefinition(
        name="sdd-stabilize",
        version="1.0.0",
        category="operations",
        description="Run stabilization checks before handoff.",
        when_to_use=["before release", "before merge"],
        outcomes=["policy_result", "next_actions"],
        allowed_tools=["providence lint run", "providence test ci-validate"],
        cli_fallback=["providence lint run", "providence test ci-validate"],
        required_permissions=["workspace-read"],
        capability_id="stabilize",
        risk_score="medium",
        tags=["stability", "quality-gate"],
        triggers=[
            "before release",
            "before merge",
            "quality gate",
            "stabilize",
            "pre-handoff",
            "ci validation",
            "lint",
            "ready to ship",
        ],
        forbidden=[
            "modify files",
            "auto-fix lint errors",
            "skip failing checks",
            "mark as stable when checks fail",
        ],
        fallback_to="sdd-diagnose",
        idempotent=True,
        context_policy={"max_context_tokens": 1200, "default_detail": "minimal"},
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
    "sdd-compress-context": SkillDefinition(
        name="sdd-compress-context",
        version="1.0.0",
        category="economy",
        description="Reduce context footprint while preserving governance context.",
        when_to_use=["high token usage", "long sessions"],
        outcomes=["policy_result", "next_actions"],
        allowed_tools=["providence runtime status"],
        cli_fallback=["providence runtime status"],
        required_permissions=["workspace-read"],
        capability_id="compress_context",
        risk_score="low",
        tags=["token-economy", "context"],
        budget_policy={
            "token_budget": TOKEN_BUDGET_LOW,
            "timeout_seconds": 60,
            "max_retries": 1,
        },
        triggers=[
            "high token usage",
            "context limit",
            "compress",
            "token budget exhausted",
            "long session",
            "context full",
        ],
        forbidden=[
            "modify files",
            "apply fixes",
            "run tests",
            "write output outside context summary",
        ],
        fallback_to=None,
        idempotent=True,
        context_policy={"max_context_tokens": 600, "default_detail": "minimal"},
    ),
}
