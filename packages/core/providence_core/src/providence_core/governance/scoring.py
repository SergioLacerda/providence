"""Governance scoring utilities — centralized computation logic.

Consolidates governance score calculation to ensure consistency across
CLI commands (doctor, governance score) and integrations.
"""

from typing import TypedDict


class ScoreCheck(TypedDict):
    """A single check in the governance score calculation."""

    label: str
    passed: bool
    weight: int


def compute_governance_score(
    checks: list[ScoreCheck] | list[tuple[str, bool, int]],
) -> int:
    """Compute weighted governance score from check results.

    Args:
        checks: List of (label, passed, weight) tuples or ScoreCheck dicts.
                The canonical weights are:
                  - profile validation: 30
                  - artifacts validation: 30
                  - AHP confidence: 20
                  - core_hash match: 20
                  Total: 100

    Returns:
        Governance score (0-100).
    """
    if not checks:
        return 0

    # Normalize to tuples if ScoreCheck dicts provided
    normalized = []
    for check in checks:
        if isinstance(check, dict):
            normalized.append((check["label"], check["passed"], check["weight"]))
        else:
            normalized.append(check)

    weighted_passed = sum(w for _, passed, w in normalized if passed)
    weighted_total = sum(w for _, _, w in normalized)

    if weighted_total == 0:
        return 0

    return round((weighted_passed / weighted_total) * 100)
