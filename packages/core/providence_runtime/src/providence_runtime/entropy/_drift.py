"""Cross-session PATH drift detection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# PATH classification — "heavy" paths that indicate broad task scoping
# ---------------------------------------------------------------------------

_HEAVY_PATHS: frozenset[str] = frozenset({"C", "D"})
_OVERLOAD_DOMINANCE_PCT: float = 50.0  # heavy path > 50% of tasks = overloaded


@dataclass
class PathDistribution:
    """PATH classification distribution across a set of events.

    Attributes
    ----------
    counts:
        Map of path_id → event count.
    total:
        Total events with a non-empty path_id.
    dominant_path:
        The path_id with the highest count (empty string when total=0).
    is_overloaded:
        True when a "heavy" PATH (C or D) accounts for more than
        :data:`_OVERLOAD_DOMINANCE_PCT` percent of tasks.
    reason:
        Human-readable assessment message.
    """

    counts: dict[str, int]
    total: int
    dominant_path: str
    is_overloaded: bool
    reason: str


class SessionDriftScorer:
    """Detects systematic PATH overloading by analyzing event history.

    A session is considered overloaded when PATH C (complex feature) or
    PATH D (multi-thread) accounts for more than 50% of tasks across sessions —
    indicating that work is being scoped too broadly rather than decomposed.

    Usage::

        # From in-memory events
        distribution = SessionDriftScorer.from_events(sink.list_events())
        if distribution.is_overloaded:
            reason = distribution.reason

        # From JSONL audit log
        distribution = SessionDriftScorer.from_jsonl(Path(".providence/runtime/compliance-events.jsonl"))
    """

    @staticmethod
    def from_events(events: list[Any]) -> PathDistribution:
        """Compute PATH distribution from a list of ``RuntimeEvent`` objects.

        Parameters
        ----------
        events:
            Any sequence of objects with a ``path_id`` attribute.
        """
        counts: dict[str, int] = {}
        for evt in events:
            pid = getattr(evt, "path_id", "") or ""
            if pid:
                counts[pid] = counts.get(pid, 0) + 1
        return SessionDriftScorer._make_distribution(counts)

    @staticmethod
    def from_jsonl(jsonl_path: Path) -> PathDistribution:
        """Compute PATH distribution from a JSONL compliance log file.

        Parameters
        ----------
        jsonl_path:
            Path to the JSONL audit log.  Returns an empty distribution when
            the file does not exist.
        """
        counts: dict[str, int] = {}
        if not jsonl_path.exists():
            return SessionDriftScorer._make_distribution(counts)
        with jsonl_path.open(encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    pid = data.get("path_id", "") or ""
                    if pid:
                        counts[pid] = counts.get(pid, 0) + 1
                except json.JSONDecodeError:
                    continue
        return SessionDriftScorer._make_distribution(counts)

    @staticmethod
    def _make_distribution(counts: dict[str, int]) -> PathDistribution:
        total = sum(counts.values())
        if total == 0:
            return PathDistribution(
                counts=counts,
                total=0,
                dominant_path="",
                is_overloaded=False,
                reason="[SDD] No path_id data available for drift analysis.",
            )
        dominant_path = max(counts, key=lambda k: counts[k])
        dominant_count = counts[dominant_path]
        dominant_pct = dominant_count / total * 100.0
        is_overloaded = (
            dominant_path in _HEAVY_PATHS and dominant_pct > _OVERLOAD_DOMINANCE_PCT
        )
        if is_overloaded:
            reason = (
                f"[SDD] PATH {dominant_path} dominates at {dominant_pct:.1f}% of tasks "
                f"(>{_OVERLOAD_DOMINANCE_PCT:.0f}% threshold). "
                "Systematic overloading detected — review task scoping."
            )
        else:
            reason = (
                f"[SDD] PATH distribution within bounds. "
                f"Dominant path: {dominant_path} ({dominant_pct:.1f}%)."
            )
        return PathDistribution(
            counts=counts,
            total=total,
            dominant_path=dominant_path,
            is_overloaded=is_overloaded,
            reason=reason,
        )
