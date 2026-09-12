"""
Confidence scoring for skill routing decisions.
Reference: skillsV6.md §6.2

All computation is deterministic (no LLM calls).
Same input always produces the same output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# Fixed weights — configurable per project via skill.yaml confidence_weights,
# but the algorithm (weighted average) is always this function.
DEFAULT_WEIGHTS: Final[dict[str, float]] = {
    "intent": 0.30,
    "route": 0.25,
    "scope": 0.20,
    "risk": 0.15,
    "validation": 0.10,
}

REQUIRED_DIMENSIONS: Final[frozenset[str]] = frozenset(DEFAULT_WEIGHTS.keys())


@dataclass(frozen=True)
class ConfidenceScores:
    """ConfidenceScores."""

    intent: float
    route: float
    scope: float
    risk: float
    validation: float
    overall: float

    def as_dict(self) -> dict[str, float]:
        """As Dict."""
        return {
            "intent": self.intent,
            "route": self.route,
            "scope": self.scope,
            "risk": self.risk,
            "validation": self.validation,
            "overall": self.overall,
        }


def compute_overall_confidence(
    scores: dict[str, float],
    weights: dict[str, float] | None = None,
) -> ConfidenceScores:
    """
    Weighted average of per-dimension confidence scores.

    All dimensions are required. Weights default to DEFAULT_WEIGHTS.
    Raises ValueError if any dimension is missing or out of [0.0, 1.0].
    """
    effective_weights = weights if weights is not None else DEFAULT_WEIGHTS

    missing = REQUIRED_DIMENSIONS - set(scores.keys())
    if missing:
        raise ValueError(f"Missing confidence dimensions: {sorted(missing)}")

    extra = set(scores.keys()) - REQUIRED_DIMENSIONS
    if extra:
        raise ValueError(f"Unknown confidence dimensions: {sorted(extra)}")

    for dim, value in scores.items():
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                f"Confidence score for '{dim}' must be in [0.0, 1.0], got {value}"
            )

    overall = sum(scores[dim] * effective_weights[dim] for dim in effective_weights)

    return ConfidenceScores(
        intent=scores["intent"],
        route=scores["route"],
        scope=scores["scope"],
        risk=scores["risk"],
        validation=scores["validation"],
        overall=round(overall, 4),
    )


# Thresholds — aligned with skill.yaml confidence_policy
EXECUTE_THRESHOLD: Final[float] = 0.85
CONSERVATIVE_THRESHOLD: Final[float] = 0.65
INTAKE_THRESHOLD: Final[float] = 0.45


def interpret_confidence(overall: float) -> str:
    """
    Interpret an overall confidence score as an execution decision.

    Returns one of: 'execute', 'conservative', 'intake', 'degraded'.
    Deterministic — same input always returns same decision.
    """
    if overall >= EXECUTE_THRESHOLD:
        return "execute"
    if overall >= CONSERVATIVE_THRESHOLD:
        return "conservative"
    if overall >= INTAKE_THRESHOLD:
        return "intake"
    return "degraded"
