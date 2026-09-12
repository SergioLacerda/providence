"""LocalIntelligenceProvider — heuristic-based always-available provider."""

from __future__ import annotations

from .._models import (
    AnalysisResult,
    BudgetEstimate,
    CompressedContext,
    ContextBundle,
    TaskContext,
)
from ._constants import (
    _BUDGET_MAX_BYTES,
    _BUDGET_MIN_BYTES,
    _BYTES_PER_QUERY_CHAR,
    _COMPLEXITY_HIGH,
    _COMPLEXITY_HIGH_THRESHOLD,
    _COMPLEXITY_LOW,
    _COMPLEXITY_LOW_THRESHOLD,
    _COMPLEXITY_MED,
    _LOCAL_CONFIDENCE,
    _PATH_FROM_BUDGET,
    _PATH_HIGH_COMPLEXITY,
    _PATH_SUGGESTION,
    _TASK_CLASS_KEYWORDS,
)


class LocalIntelligenceProvider:
    """Heuristic-based intelligence provider using keyword matching and size rules.

    Always available (no external dependencies, no I/O, no network).
    Provides baseline quality for PATH routing, context compression, and
    budget estimation that is sufficient for correct harness operation.
    """

    @property
    def name(self) -> str:
        """Name."""
        return "local"

    @property
    def available(self) -> bool:
        """Available."""
        return True

    def analyze_task(self, task: TaskContext) -> AnalysisResult:
        """Classify the task with keyword heuristics and query length scoring.

        Task class: first keyword match wins.  Complexity: derived from the
        number of characters in ``task.query``.  Suggested PATH: table lookup
        with a hard override to PATH C for high-complexity tasks.
        """
        query_lower = task.query.lower()

        # 1. Task class via keyword matching.
        task_class = "unknown"
        matched_keywords: list[str] = []
        for cls, kws in _TASK_CLASS_KEYWORDS.items():
            hits = [kw for kw in kws if kw in query_lower]
            if hits:
                task_class = cls
                matched_keywords = hits
                break

        # 2. Complexity from query length.
        q_len = len(task.query)
        if q_len < _COMPLEXITY_LOW_THRESHOLD:
            complexity = _COMPLEXITY_LOW
            band = "low"
        elif q_len <= _COMPLEXITY_HIGH_THRESHOLD:
            complexity = _COMPLEXITY_MED
            band = "medium"
        else:
            complexity = _COMPLEXITY_HIGH
            band = "high"

        # 3. Suggested PATH.
        if band == "high":
            suggested_path = _PATH_HIGH_COMPLEXITY
        else:
            suggested_path = _PATH_SUGGESTION.get((task_class, band), "B")

        return AnalysisResult(
            task_class=task_class,
            complexity_score=complexity,
            suggested_path_id=suggested_path,
            keywords=list(dict.fromkeys(matched_keywords)),  # dedup, preserve order
            provider=self.name,
        )

    def compress_context(self, context: ContextBundle) -> CompressedContext:
        """Compress context by deduplicating then truncating to budget_bytes.

        Strategy:
        1. Remove exact-duplicate items (first occurrence wins).
        2. Drop items from the end until accumulated size ≤ ``budget_bytes``.
        """
        # Deduplicate preserving insertion order.
        seen: set[str] = set()
        deduped: list[str] = []
        for item in context.items:
            if item not in seen:
                seen.add(item)
                deduped.append(item)

        original_bytes = sum(len(item.encode()) for item in context.items)

        # Truncate to budget — always include the first item even if oversized.
        compressed: list[str] = []
        accumulated = 0
        for item in deduped:
            item_bytes = len(item.encode())
            if accumulated + item_bytes > context.budget_bytes and compressed:
                break
            compressed.append(item)
            accumulated += item_bytes

        compressed_bytes = sum(len(item.encode()) for item in compressed)
        ratio = compressed_bytes / original_bytes if original_bytes > 0 else 1.0

        return CompressedContext(
            items=compressed,
            original_bytes=original_bytes,
            compressed_bytes=compressed_bytes,
            compression_ratio=round(ratio, 4),
            provider=self.name,
        )

    def estimate_budget(self, task: TaskContext) -> BudgetEstimate:
        """Estimate context bytes from query length × heuristic multiplier.

        Clamps the result between 5 KB (minimum) and 85 KB (PATH C ceiling).
        Confidence is intentionally low (0.4) — this baseline is sufficient
        for routing; semantic providers yield higher-confidence estimates.
        """
        raw = len(task.query) * _BYTES_PER_QUERY_CHAR
        estimated = max(_BUDGET_MIN_BYTES, min(raw, _BUDGET_MAX_BYTES))

        suggested_path = "C"  # default for large estimates
        for ceiling, path in _PATH_FROM_BUDGET:
            if estimated <= ceiling:
                suggested_path = path
                break

        return BudgetEstimate(
            estimated_bytes=estimated,
            suggested_path_id=suggested_path,
            confidence=_LOCAL_CONFIDENCE,
            provider=self.name,
        )
