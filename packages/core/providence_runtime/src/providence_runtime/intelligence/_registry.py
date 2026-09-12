"""Provider registry with graceful degradation to the local provider."""

from __future__ import annotations

from ._models import (
    AnalysisResult,
    BudgetEstimate,
    CompressedContext,
    ContextBundle,
    TaskContext,
)
from ._provider import IntelligenceProvider, LocalIntelligenceProvider


class ProviderRegistry:
    """Orchestrates intelligence providers with graceful degradation.

    Providers are tried in registration order; the first ``available`` one
    wins.  When no registered provider is available the registry falls back
    to the built-in :class:`LocalIntelligenceProvider`, which is always
    available.

    This invariant guarantees that :meth:`analyze_task`,
    :meth:`compress_context`, and :meth:`estimate_budget` never raise due
    to provider unavailability.

    Parameters
    ----------
    providers:
        Ordered list of providers to try before the local fallback.  Pass
        ``None`` or an empty list to use only the local provider.
    """

    def __init__(
        self,
        providers: list[IntelligenceProvider] | None = None,
    ) -> None:
        self._providers: list[IntelligenceProvider] = list(providers or [])
        self._local = LocalIntelligenceProvider()

    def _active(self) -> IntelligenceProvider:
        """Return the first available provider; fall back to local."""
        for p in self._providers:
            if p.available:
                return p
        return self._local

    @property
    def active_provider(self) -> str:
        """Name of the provider that will handle the next request."""
        return self._active().name

    def analyze_task(self, task: TaskContext) -> AnalysisResult:
        """Analyze Task."""
        return self._active().analyze_task(task)

    def compress_context(self, context: ContextBundle) -> CompressedContext:
        """Compress Context."""
        return self._active().compress_context(context)

    def estimate_budget(self, task: TaskContext) -> BudgetEstimate:
        """Estimate Budget."""
        return self._active().estimate_budget(task)
