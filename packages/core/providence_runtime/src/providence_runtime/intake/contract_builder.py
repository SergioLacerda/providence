"""Governed intake — intake-contract field builder.

Relocated from `providence_cli.services.ask_response_intake`
(`.analysis/pending/20260907-backend-governance-reorg-refinement`, Fase 1).

`AskHandler.pre_run()` (`_skill_executor/_handlers/_ask.py`) builds a separate,
differently-shaped `execution_contract` via `_build_execution_contract`
(`_skill_executor/_context_builders/_contracts.py`) for the distinct
`providence skills run sdd-ask` code path. Fase 2
(`.analysis/refined/20260908-execution-contract-unification`) found the two
objects never co-occur in one request and deferred merging them to Fase 3;
both gained a `schema_version`/`origin` pair instead so each is
independently versioned and traceable.
"""

from __future__ import annotations

from typing import Any

from .entrypoint import resolve_ask_entrypoint
from .intent import classify_ask_intent
from .routing import resolve_ask_next_action


def build_intake_contract_fields(
    *, execution_gate: str, query: str, skill: str | None
) -> dict[str, Any]:
    """Build the additive structured-intake fields shared by text/JSON output.

    These fields are additive to the existing `execution_gate`,
    `intake_index_mode`, and `next_valid_path` signals — they do not replace
    or rename them. `delegation_executed` and `provider_bound` are always
    `false`: no provider invocation path exists yet in `providence ask` (see spike
    analysis A-001 Q4).
    """
    intent = classify_ask_intent(query, skill)
    entrypoint, explicit_command = resolve_ask_entrypoint()
    return {
        "schema_version": "1.0",
        "origin": "cli_intake",
        "intent": intent,
        "entrypoint": entrypoint,
        "explicit_command": explicit_command,
        "next_action": resolve_ask_next_action(execution_gate, intent),
        "delegation_executed": False,
        "provider_bound": False,
        "handoff_owner": "calling_agent",
        "requires_user_approval": intent == "implementation_request",
    }
