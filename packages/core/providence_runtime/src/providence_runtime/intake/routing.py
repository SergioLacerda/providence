"""Governed intake — next-action routing.

Relocated from `providence_cli.services.ask_response_intake`
(`.analysis/pending/20260907-backend-governance-reorg-refinement`, Fase 1).
"""

from __future__ import annotations


def resolve_ask_next_action(execution_gate: str, intent: str) -> str:
    """Resolve the single next action a calling agent should take."""
    if execution_gate == "blocked":
        return "acknowledge_context"
    if intent == "implementation_request":
        return "create_execution_contract"
    return "answer_from_governance"
