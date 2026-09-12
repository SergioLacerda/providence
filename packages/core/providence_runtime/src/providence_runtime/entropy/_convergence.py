"""Convergence detection via least-squares trend on utilization samples."""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Convergence thresholds
# ---------------------------------------------------------------------------

_CONVERGENCE_WINDOW: int = 3
_DIVERGENCE_SLOPE_THRESHOLD: float = 2.0  # pct/step — growing faster = diverging


def _compute_trend(samples: list[float]) -> float:
    """Least-squares slope of the sample series.

    Positive return value means utilization is growing (diverging);
    negative means it is shrinking (converging).
    """
    n = len(samples)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(samples) / n
    numerator = sum((i - x_mean) * (samples[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    return numerator / denominator if denominator != 0.0 else 0.0


@dataclass
class ConvergenceReport:
    """Result of a convergence assessment.

    Attributes
    ----------
    is_converging:
        True when the trend slope is within the divergence threshold.
    samples:
        The utilization percentages used in this assessment.
    trend:
        Least-squares slope (pct/step).  Positive = growing utilization.
    reason:
        Human-readable assessment message.
    """

    is_converging: bool
    samples: list[float]
    trend: float
    reason: str


class ConvergenceTracker:
    """Tracks a series of ``budget_utilization_pct`` values and detects divergence.

    Uses a sliding window of the last ``window`` observations.  When the slope
    of the window exceeds :data:`_DIVERGENCE_SLOPE_THRESHOLD` pct/step, the
    agent is consuming context faster than it is making progress.

    Parameters
    ----------
    window:
        Number of recent samples to include in slope calculation (default: 3).
    """

    def __init__(self, window: int = _CONVERGENCE_WINDOW) -> None:
        self._samples: list[float] = []
        self._window = window

    def record(self, pct: float) -> None:
        """Append a new utilization percentage observation."""
        self._samples.append(pct)

    def report(self) -> ConvergenceReport:
        """Return a convergence assessment of the current sample window."""
        window_samples = self._samples[-self._window :]
        if len(window_samples) < 2:
            return ConvergenceReport(
                is_converging=True,
                samples=list(window_samples),
                trend=0.0,
                reason="[SDD] Insufficient samples for convergence assessment.",
            )
        trend = _compute_trend(window_samples)
        is_converging = trend <= _DIVERGENCE_SLOPE_THRESHOLD
        if is_converging:
            reason = (
                f"[SDD] Utilization trend {trend:.2f}%/step ≤ threshold "
                f"{_DIVERGENCE_SLOPE_THRESHOLD:.2f}%/step. Task is converging."
            )
        else:
            reason = (
                f"[SDD] Utilization trend {trend:.2f}%/step > threshold "
                f"{_DIVERGENCE_SLOPE_THRESHOLD:.2f}%/step. "
                "Budget consumption outpacing progress — consider task decomposition."
            )
        return ConvergenceReport(
            is_converging=is_converging,
            samples=list(window_samples),
            trend=trend,
            reason=reason,
        )
