"""Entropy score computation and decomposition advisor."""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Entropy thresholds per PATH
# Set at 50% of the theoretical maximum:
#   PATH A/D: max = retry_ceil(2) × reflection_ceil(1) × 100/100 = 2.0  → 1.0
#   PATH B/C: max = retry_ceil(3) × reflection_ceil(2) × 100/100 = 6.0  → 3.0
# ---------------------------------------------------------------------------

_PATH_ENTROPY_THRESHOLD: dict[str, float] = {
    "A": 1.0,
    "B": 3.0,
    "C": 3.0,
    "D": 1.0,
}
_DEFAULT_ENTROPY_THRESHOLD: float = 1.0  # most conservative (PATH A)


@dataclass
class EntropyScore:
    """Cognitive entropy measurement for a single task execution.

    Attributes
    ----------
    retry_count:
        Number of retries consumed so far.
    reflection_count:
        Number of reflection cycles consumed so far.
    budget_utilization_pct:
        Context budget utilization percentage (0–100+).
    path_id:
        Active PATH identifier ("A" | "B" | "C" | "D").
    score:
        Composite entropy score: ``retry_count × reflection_count ×
        budget_utilization_pct / 100``.
    """

    retry_count: int
    reflection_count: int
    budget_utilization_pct: float
    path_id: str
    score: float

    @classmethod
    def compute(
        cls,
        retry_count: int,
        reflection_count: int,
        budget_utilization_pct: float,
        path_id: str = "",
    ) -> EntropyScore:
        """Compute the entropy score from raw counters.

        Parameters
        ----------
        retry_count:
            Retries consumed for the current task.
        reflection_count:
            Reflection cycles consumed for the current task.
        budget_utilization_pct:
            Current context budget utilization (0–100+).
        path_id:
            Active PATH ("A" | "B" | "C" | "D").  Unknown values are accepted;
            the advisor applies the most conservative threshold.
        """
        score = retry_count * reflection_count * budget_utilization_pct / 100.0
        return cls(
            retry_count=retry_count,
            reflection_count=reflection_count,
            budget_utilization_pct=budget_utilization_pct,
            path_id=path_id,
            score=score,
        )


@dataclass
class DecompositionSuggestion:
    """Advisor result for a single entropy evaluation.

    Attributes
    ----------
    should_decompose:
        True when the entropy score exceeds the PATH threshold.
    reason:
        Human-readable explanation with score, threshold, and PATH info.
    entropy_score:
        Computed composite entropy value.
    threshold:
        PATH-specific threshold used for the evaluation.
    path_id:
        Active PATH at evaluation time.
    """

    should_decompose: bool
    reason: str
    entropy_score: float
    threshold: float
    path_id: str


class EntropyAdvisor:
    """Advises on task decomposition based on cognitive entropy.

    Usage example::

        advisor = EntropyAdvisor()
        suggestion = advisor.advise(
            retry_count=budget.retry_count,
            reflection_count=budget.reflection_count,
            budget_utilization_pct=pct,
            path_id="A",
        )
        if suggestion.should_decompose:
            typer.echo(suggestion.reason, err=True)
    """

    def advise(
        self,
        retry_count: int,
        reflection_count: int,
        budget_utilization_pct: float,
        path_id: str = "",
    ) -> DecompositionSuggestion:
        """Evaluate whether the current entropy warrants task decomposition.

        Returns a :class:`DecompositionSuggestion` whose ``should_decompose``
        field is ``True`` when ``entropy_score > threshold`` (strict greater-than
        — a score exactly at the threshold is still within acceptable bounds).
        """
        score = EntropyScore.compute(
            retry_count=retry_count,
            reflection_count=reflection_count,
            budget_utilization_pct=budget_utilization_pct,
            path_id=path_id,
        )
        threshold = _PATH_ENTROPY_THRESHOLD.get(path_id, _DEFAULT_ENTROPY_THRESHOLD)
        should_decompose = score.score > threshold
        path_info = f" (PATH {path_id})" if path_id else ""
        if should_decompose:
            reason = (
                f"[SDD] Entropy score {score.score:.2f} exceeds threshold "
                f"{threshold:.2f}{path_info}. "
                "Task should be decomposed into smaller PATH A/B units."
            )
        else:
            reason = (
                f"[SDD] Entropy score {score.score:.2f} within threshold "
                f"{threshold:.2f}{path_info}. No decomposition required."
            )
        return DecompositionSuggestion(
            should_decompose=should_decompose,
            reason=reason,
            entropy_score=score.score,
            threshold=threshold,
            path_id=path_id,
        )
