"""Cognitive entropy scoring — Phase 4 proactive degradation detection.

Implements the composite entropy metric, convergence detection, and cross-session
drift analysis defined in §economy/efficiency-policy.md.

Entropy score formula (§economy/efficiency-policy.md):
    score = retry_count * reflection_count * budget_utilization_pct / 100

When the score exceeds the PATH threshold, the agent should decompose the task
into smaller PATH A/B units rather than continuing.
"""

from __future__ import annotations

from ._convergence import (
    _DIVERGENCE_SLOPE_THRESHOLD,
    ConvergenceReport,
    ConvergenceTracker,
)
from ._drift import PathDistribution, SessionDriftScorer
from ._score import (
    _DEFAULT_ENTROPY_THRESHOLD,
    _PATH_ENTROPY_THRESHOLD,
    DecompositionSuggestion,
    EntropyAdvisor,
    EntropyScore,
)

__all__ = [
    "ConvergenceReport",
    "ConvergenceTracker",
    "DecompositionSuggestion",
    "EntropyAdvisor",
    "EntropyScore",
    "PathDistribution",
    "SessionDriftScorer",
    "_DEFAULT_ENTROPY_THRESHOLD",
    "_DIVERGENCE_SLOPE_THRESHOLD",
    "_PATH_ENTROPY_THRESHOLD",
]
