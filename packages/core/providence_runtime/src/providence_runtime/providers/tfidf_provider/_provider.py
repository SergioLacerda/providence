"""TfidfProvider — TF-IDF similarity-based context analysis and compression."""

from __future__ import annotations

import logging

from providence_runtime.intelligence import (
    AnalysisResult,
    BudgetEstimate,
    CompressedContext,
    ContextBundle,
    TaskContext,
)

from ._similarity import _cosine_similarity as _cosine_similarity_impl
from ._similarity import _tokenize as _tokenize_impl

logger = logging.getLogger(__name__)


class TfidfProvider:
    """TF-IDF based context analysis and compression.

    Uses term frequency-inverse document frequency scoring with cosine
    similarity to rank context items by relevance to the query.

    Pure Python implementation with no external ML dependencies.
    """

    _tokenize = staticmethod(_tokenize_impl)
    _cosine_similarity = staticmethod(_cosine_similarity_impl)

    @property
    def name(self) -> str:
        """Provider name."""
        return "tfidf"

    @property
    def available(self) -> bool:
        """TF-IDF provider is always available."""
        return True

    def analyze_task(self, task: TaskContext) -> AnalysisResult:
        """Analyze task using TF-IDF similarity scoring.

        Ranks context items by relevance to the query and determines
        the best PATH based on how complex the query appears.

        Returns:
            AnalysisResult with suggested path_id and keyword matches.
        """
        try:
            query_tokens = self._tokenize(task.query)
            if not query_tokens:
                return AnalysisResult(
                    task_class="unknown",
                    complexity_score=0.5,
                    suggested_path_id="A",
                    keywords=[],
                    provider=self.name,
                )

            complexity = min(1.0, len(task.query) / 200.0)
            suggested_path_id = "C" if complexity > 0.7 else "A"

            return AnalysisResult(
                task_class="unknown",
                complexity_score=complexity,
                suggested_path_id=suggested_path_id,
                keywords=query_tokens[:5],
                provider=self.name,
            )
        except Exception as exc:
            logger.debug("TF-IDF analysis failed: %s", exc)
            return AnalysisResult(
                task_class="unknown",
                complexity_score=0.5,
                suggested_path_id="A",
                keywords=[],
                provider=self.name,
            )

    def compress_context(self, context: ContextBundle) -> CompressedContext:
        """Compress context using TF-IDF relevance scoring.

        Removes items with lowest TF-IDF similarity to the query until
        the total bytes fit within the budget. Always preserves at least
        one item (the first) even if it exceeds the budget.

        Returns:
            CompressedContext with compression_ratio = compressed_bytes / original_bytes
            (value < 1.0 indicates successful compression).
        """
        try:
            original_bytes = sum(len(item.encode()) for item in context.items)

            if not context.items:
                return CompressedContext(
                    items=[],
                    original_bytes=original_bytes,
                    compressed_bytes=0,
                    compression_ratio=1.0,
                    provider=self.name,
                )

            # Score items by TF-IDF similarity to query
            query_tokens = self._tokenize(context.query)
            if not query_tokens:
                # No tokens — keep first item only
                first_item = context.items[0]
                compressed_bytes = len(first_item.encode())
                ratio = (
                    original_bytes / compressed_bytes if compressed_bytes > 0 else 1.0
                )
                return CompressedContext(
                    items=[first_item],
                    original_bytes=original_bytes,
                    compressed_bytes=compressed_bytes,
                    compression_ratio=ratio,
                    provider=self.name,
                )

            scores = []
            for i, item in enumerate(context.items):
                item_tokens = self._tokenize(item)
                score = self._cosine_similarity(query_tokens, item_tokens)
                scores.append((score, i, item))

            # Sort by relevance (highest first)
            scores.sort(key=lambda x: x[0], reverse=True)

            # Greedily select items until budget exceeded
            selected = []
            accumulated_bytes = 0
            for _score, idx, item in scores:
                item_bytes = len(item.encode())
                if accumulated_bytes + item_bytes <= context.budget_bytes:
                    selected.append((idx, item))  # Keep original order
                    accumulated_bytes += item_bytes
                elif not selected:
                    # Must keep at least one item
                    selected.append((idx, item))
                    accumulated_bytes = item_bytes
                    break

            # Restore original order
            selected.sort(key=lambda x: x[0])
            compressed_items = [item for _, item in selected]
            compressed_bytes = accumulated_bytes

            ratio = compressed_bytes / original_bytes if original_bytes > 0 else 1.0

            return CompressedContext(
                items=compressed_items,
                original_bytes=original_bytes,
                compressed_bytes=compressed_bytes,
                compression_ratio=ratio,
                provider=self.name,
            )
        except Exception as exc:
            logger.debug("TF-IDF compression failed: %s", exc)
            # Fallback: return all items
            compressed_bytes = sum(len(item.encode()) for item in context.items)
            return CompressedContext(
                items=context.items,
                original_bytes=compressed_bytes,
                compressed_bytes=compressed_bytes,
                compression_ratio=1.0,
                provider=self.name,
            )

    def estimate_budget(self, task: TaskContext) -> BudgetEstimate:
        """Estimate required budget using simple heuristic.

        Estimates based on query length and context bytes loaded.

        Returns:
            BudgetEstimate with estimated_bytes and suggested_path_id.
        """
        try:
            estimated = len(task.query) * 8
            estimated = max(5_000, min(85_000, estimated))

            complexity = min(1.0, len(task.query) / 200.0)
            suggested_path_id = "C" if complexity > 0.7 else "A"

            return BudgetEstimate(
                estimated_bytes=estimated,
                suggested_path_id=suggested_path_id,
                confidence=0.4,
                provider=self.name,
            )
        except Exception as exc:
            logger.debug("TF-IDF budget estimation failed: %s", exc)
            return BudgetEstimate(
                estimated_bytes=50_000,
                suggested_path_id="A",
                confidence=0.2,
                provider=self.name,
            )
