"""RuleCandidate — a proposed guardrail derived from recurring failures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleCandidate:
    """RuleCandidate."""

    candidate_id: str
    pattern: str
    proposed_guardrail: str
    risk_level: str
    expected_impact: str
    evidence_refs: list[str]
    source_count: int
    created_at: str
