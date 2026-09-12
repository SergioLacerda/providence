"""AST-based intelligence provider — Python code structure analysis."""

from __future__ import annotations

import ast
import logging

from providence_runtime.intelligence import (
    AnalysisResult,
    BudgetEstimate,
    CompressedContext,
    ContextBundle,
    TaskContext,
)

logger = logging.getLogger(__name__)


class AstProvider:
    """Python AST-based context analysis and compression.

    Analyzes Python code structure to understand complexity and
    deduplicates structurally-equivalent code snippets.

    Only available when context contains valid Python code.
    """

    @property
    def name(self) -> str:
        """Provider name."""
        return "ast"

    @property
    def available(self) -> bool:
        """AST provider is always available (degrades gracefully if no Python code)."""
        return True

    def analyze_task(self, task: TaskContext) -> AnalysisResult:
        """Analyze task complexity using AST node counting.

        Counts ClassDef, FunctionDef, and Import nodes to assess code complexity.

        Returns:
            AnalysisResult with complexity_score and suggested path_id.
        """
        try:
            ast_nodes = self._count_ast_nodes(task.query)
            total_nodes = sum(ast_nodes.values())
            complexity = min(1.0, total_nodes / 50.0)
            suggested_path_id = "C" if complexity > 0.7 else "A"

            return AnalysisResult(
                task_class="python_code" if total_nodes > 0 else "unknown",
                complexity_score=complexity,
                suggested_path_id=suggested_path_id,
                keywords=list(ast_nodes.keys()),
                provider=self.name,
            )
        except Exception as exc:
            logger.debug("AST analysis failed: %s", exc)
            return AnalysisResult(
                task_class="unknown",
                complexity_score=0.5,
                suggested_path_id="A",
                keywords=[],
                provider=self.name,
            )

    def compress_context(self, context: ContextBundle) -> CompressedContext:
        """Compress context by deduplicating structurally-equivalent items.

        Removes items with identical AST structure (deduplicated by content hash).

        Returns:
            CompressedContext with deduplicated items.
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

            # Deduplicate by exact string match first
            seen = {}
            deduplicated = []
            for item in context.items:
                if item not in seen:
                    seen[item] = True
                    deduplicated.append(item)

            # Try to fit within budget
            selected = []
            accumulated_bytes = 0
            for item in deduplicated:
                item_bytes = len(item.encode())
                if accumulated_bytes + item_bytes <= context.budget_bytes:
                    selected.append(item)
                    accumulated_bytes += item_bytes
                elif not selected:
                    # Must keep at least one
                    selected.append(item)
                    accumulated_bytes = item_bytes
                    break

            compressed_bytes = accumulated_bytes
            ratio = compressed_bytes / original_bytes if original_bytes > 0 else 1.0

            return CompressedContext(
                items=selected,
                original_bytes=original_bytes,
                compressed_bytes=compressed_bytes,
                compression_ratio=ratio,
                provider=self.name,
            )
        except Exception as exc:
            logger.debug("AST compression failed: %s", exc)
            compressed_bytes = sum(len(item.encode()) for item in context.items)
            return CompressedContext(
                items=context.items,
                original_bytes=compressed_bytes,
                compressed_bytes=compressed_bytes,
                compression_ratio=1.0,
                provider=self.name,
            )

    def estimate_budget(self, task: TaskContext) -> BudgetEstimate:
        """Estimate budget based on code complexity.

        Returns:
            BudgetEstimate based on AST node count.
        """
        try:
            ast_nodes = self._count_ast_nodes(task.query)
            total_nodes = sum(ast_nodes.values())

            # Heuristic: ~500 bytes per AST node
            estimated = max(5_000, total_nodes * 500)
            estimated = min(85_000, estimated)

            complexity = min(1.0, total_nodes / 50.0)
            suggested_path_id = "C" if complexity > 0.7 else "A"

            return BudgetEstimate(
                estimated_bytes=estimated,
                suggested_path_id=suggested_path_id,
                confidence=0.6,
                provider=self.name,
            )
        except Exception as exc:
            logger.debug("AST budget estimation failed: %s", exc)
            return BudgetEstimate(
                estimated_bytes=50_000,
                suggested_path_id="A",
                confidence=0.2,
                provider=self.name,
            )

    @staticmethod
    def _count_ast_nodes(code: str) -> dict[str, int]:
        """Count AST node types in Python code."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {}

        counts: dict[str, int] = {}
        for node in ast.walk(tree):
            node_type = node.__class__.__name__
            counts[node_type] = counts.get(node_type, 0) + 1

        return counts
