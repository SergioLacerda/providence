"""Hardcoded fallback skill registry definitions: orchestrator skills."""

from __future__ import annotations

from ..._skill_contracts import TOKEN_BUDGET_MEDIUM, SkillDefinition

__all__ = ["_ORCHESTRATION_SKILLS"]

_ORCHESTRATION_SKILLS: dict[str, SkillDefinition] = {
    "sdd-ask": SkillDefinition(
        name="sdd-ask",
        version="1.0.0",
        category="orchestrator",
        description="Query governed SDD context and report execution gates. Does not execute provider delegation.",
        when_to_use=[
            "any user request requiring skill routing",
            "before any other skill",
            "operational fix",
            "diagnostic",
            "analysis",
        ],
        outcomes=[
            "governance_context",
            "execution_gate",
            "intake_index_mode",
            "implementation_handoff",
        ],
        allowed_tools=[
            "providence ask",
            "providence governance validate",
            "providence runtime status --force",
        ],
        cli_fallback=[
            "providence runtime status --force",
            "providence governance validate",
        ],
        required_permissions=["workspace-read"],
        capability_id="query",
        risk_score="controlled",
        tags=["orchestrator", "routing", "entrypoint"],
        budget_policy={
            "token_budget": TOKEN_BUDGET_MEDIUM,
            "timeout_seconds": 180,
            "max_retries": 1,
        },
        escalation_policy={
            "mode": "warn",
            "require_human_on": [
                "drift.critical",
                "governance.violation",
                "contract.invalid",
            ],
        },
        triggers=[
            "any request",
            "route",
            "classify",
            "help",
            "fix",
            "diagnose",
            "analyze",
        ],
        forbidden=[
            "execute skills without execution_contract",
            "skip confidence gate",
            "skip drift check",
            "route to skill with circuit_open",
        ],
        fallback_to=None,
        idempotent=False,
        context_policy={"max_context_tokens": 1200, "default_detail": "minimal"},
        delegation_policy={
            "enabled": False,
            "runtime_status": "not_implemented",
            "current_contract": "query_only",
            "metadata_status": (
                "declarative_only: no runtime code path in providence_cli's ask "
                "pipeline reads this object today (spike: "
                "20260714-sdd-ask-single-entrypoint-spike, analysis A-002). "
                "The fields below describe a future delegation contract, not "
                "current behavior. providence ask independently reports "
                "delegation_executed=false and provider_bound=false at "
                "runtime regardless of this metadata."
            ),
            "triggers": [
                "analyze and plan",
                "create implementation plan",
                "implementation plan",
                "analysis mission",
                "orchestrate",
                "multi-phase analysis",
            ],
            "future_delegate_to": "analysis_orchestrator",
            "plugin_registry": ".providence/plugins/registry.yaml",
            "unsupported_intent_response": "implementation_handoff",
            "input_transform": {
                "user_prompt": "mission_contract",
                "reviewed_task": "direct_execution",
            },
            "result_handling": {
                "validate_against": ".providence/contracts/mission-result.schema.yaml",
                "on_invalid": "emit_governance_violation",
                "on_no_provider": "error_no_analysis_provider_registered",
            },
        },
        hard_mode_protocol={
            "read_field": "execution_gate",
            "on_blocked": [
                {"emit": "GovernanceEvent"},
                {"action": "report_to_user"},
                {"action": "stop"},
            ],
            "on_allowed": "continue",
        },
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
            ],
            "forbidden_behaviors": [
                "self_authorize_git_on_task_completion",
                "proceed_when_gate_blocked",
                "hide_intake_index_mode_none",
                "describe_intake_index_mode_none_as_gate_blocked_when_execution_gate_allowed",
            ],
        },
    ),
    "sdd-pipeline": SkillDefinition(
        name="sdd-pipeline",
        version="1.0.0",
        category="orchestrator",
        description="Orchestrate ask -> diagnose -> correct -> converge as a governed skill pipeline.",
        when_to_use=[
            "strict end-to-end correction flow",
            "pipeline orchestration",
            "multi-stage governed remediation",
        ],
        outcomes=["ask_result", "diagnosis_report", "gate_decision", "delta_report"],
        allowed_tools=[
            "providence ask",
            "providence skills run sdd-diagnose",
            "providence skills run sdd-correct",
            "providence skills run sdd-converge",
        ],
        cli_fallback=[
            "providence ask --full",
            "providence skills run sdd-diagnose",
            "providence skills run sdd-correct",
            "providence skills run sdd-converge",
        ],
        required_permissions=["workspace-read", "workspace-write-controlled"],
        risk_score="controlled",
        tags=["pipeline", "orchestration", "governance"],
        triggers=["pipeline", "orchestrate", "ask diagnose correct converge"],
        forbidden=[
            "skip ask stage",
            "skip diagnosis attestation",
            "bypass governance gates",
        ],
        fallback_to="sdd-ask",
        idempotent=False,
        config={
            "pipeline": {
                "stages": [
                    "sdd-ask",
                    "sdd-diagnose",
                    "sdd-correct",
                    "sdd-converge",
                ],
                "decision_gates": {
                    "diagnose_to_correct_min_confidence": 0.7,
                },
            }
        },
    ),
}
