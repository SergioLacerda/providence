"""IntelligenceProvider Protocol.

Reference: .providence/runtime analytics design §Phase 5
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .._models import (
    AnalysisResult,
    BudgetEstimate,
    CompressedContext,
    ContextBundle,
    TaskContext,
)


@runtime_checkable
class IntelligenceProvider(Protocol):
    """Interface for cognitive intelligence providers.

    All methods MUST be safe to call unconditionally — providers that cannot
    fulfil a request should return a best-effort degraded result, never raise.
    The ``available`` property allows :class:`ProviderRegistry` to skip
    unavailable providers before attempting a call.
    """

    @property
    def name(self) -> str:
        """Stable identifier for this provider (echoed in result fields)."""
        pass

    @property
    def available(self) -> bool:
        """True when this provider can currently service requests."""
        pass

    def analyze_task(self, task: TaskContext) -> AnalysisResult:
        """Analyse a task context and return classification + complexity."""
        pass

    def compress_context(self, context: ContextBundle) -> CompressedContext:
        """Compress a context bundle to fit within ``context.budget_bytes``."""
        pass

    def estimate_budget(self, task: TaskContext) -> BudgetEstimate:
        """Estimate the context bytes required for the given task."""
        pass
