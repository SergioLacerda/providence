"""Governed intake — execution gate resolution.

Relocated from `providence_cli.services.ask_response_intake`
(`.analysis/pending/20260907-backend-governance-reorg-refinement`, Fase 1).
"""

from __future__ import annotations


def resolve_execution_gate(*, organize_used: bool, organize_reason: str) -> str:
    """Resolve `execution_gate` from the organize-intake classification.

    Shared by the full and cheap (`--intake-only`) response paths so the gate
    formula lives in exactly one place.
    """
    gate_blocked = not organize_used and organize_reason != "light_input"
    return "blocked" if gate_blocked else "allowed"
