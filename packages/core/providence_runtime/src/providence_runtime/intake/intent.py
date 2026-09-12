"""Governed intake — intent classification.

Relocated from `providence_cli.services.ask_response_intake`
(`.analysis/pending/20260907-backend-governance-reorg-refinement`, Fase 1):
`ask_response_intake.py` keeps thin re-export shims at the old path so
existing callers and test `mock.patch` targets keep working unmodified.
"""

from __future__ import annotations

_IMPLEMENTATION_INTENT_MARKERS = (
    "implement",
    "implementation",
    "implementar",
    "implementacao",
    "implementação",
    "apply change",
    "make the change",
    "fix this",
    "corrigir",
    "aplicar",
)


def _looks_like_implementation_intent(query: str) -> bool:
    normalized = query.casefold()
    return any(marker in normalized for marker in _IMPLEMENTATION_INTENT_MARKERS)


def classify_ask_intent(query: str, skill: str | None = None) -> str:
    """Classify the governed intake intent using the existing local heuristics.

    Mirrors the keyword categories already used for implementation-intent
    detection and handbook task-type inference, mapped onto the structured
    `intent` values shared by adapters (hook, slash command). No provider
    lookup or LLM-based classification is performed.
    """
    if _looks_like_implementation_intent(query):
        return "implementation_request"
    skill_value = (skill or "").strip().casefold()
    if skill_value == "planning":
        return "planning_request"
    if skill_value in {"diagnosis", "diagnose", "debug", "stabilize"}:
        return "analysis_request"
    query_value = query.casefold()
    if any(token in query_value for token in ("diagnos", "erro", "error", "fail")):
        return "analysis_request"
    if any(token in query_value for token in ("plan", "design", "proposal")):
        return "planning_request"
    return "governance_query"
