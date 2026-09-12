"""Shared percentile computation for latency collectors.

Extracted from `_ask_latency_collector.py` (T-IMPL-2,
`.analysis/refined/20260825-tp4-instrumentation-design/design.md` §
Collector Decision) so `AskLatencyCollector` and `GateLatencyCollector` share
the one piece of logic that is genuinely common between them, without either
importing from a module named for the other's domain.
"""

from __future__ import annotations

import math


def _percentile(sorted_values: list[int], pct: float) -> int:
    """Compute the ``pct``-th percentile via linear interpolation between closest ranks.

    This is the "linear interpolation between closest ranks" method (matching
    numpy's default ``np.percentile`` behavior): the rank ``k`` is computed as
    ``(n - 1) * pct / 100`` (zero-indexed), and when ``k`` falls between two
    integer indices, the result is a weighted average of the values at the
    floor and ceiling ranks, weighted by how close ``k`` is to each.

    Worked examples (hand-verified):
      values = [10, 20, 30, 40, 100] (n=5, already sorted)
        p50: k = (5-1)*0.50 = 2.0 -> exact index 2 -> 30
        p95: k = (5-1)*0.95 = 3.8 -> f=3 (40), c=4 (100)
              -> 40*(4-3.8) + 100*(3.8-3) = 40*0.2 + 100*0.8 = 8 + 80 = 88
      values = [10, 20, 30, 40] (n=4, already sorted)
        p50: k = (4-1)*0.50 = 1.5 -> f=1 (20), c=2 (30)
              -> 20*(2-1.5) + 30*(1.5-1) = 10 + 15 = 25
    """
    if not sorted_values:
        return 0
    k = (len(sorted_values) - 1) * (pct / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    lower = sorted_values[f] * (c - k)
    upper = sorted_values[c] * (k - f)
    return round(lower + upper)
