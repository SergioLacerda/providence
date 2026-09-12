"""Pluggable Intelligence Providers — Phase 5.

Defines the IntelligenceProvider Protocol and the data types for task
analysis, context compression, and budget estimation.  Provides a
LocalIntelligenceProvider (grep + heuristics, always available, offline-
capable) and a ProviderRegistry that guarantees graceful degradation: the
system always functions without any external provider.

Architecture:

    ProviderRegistry → tries providers in order → falls back to LocalIntelligenceProvider
    IntelligenceProvider (Protocol) ← LocalIntelligenceProvider  (always available)
                                    ← (future: Semantic, AST, External providers)

Graceful degradation contract (§economy/efficiency-policy.md):
    The system MUST function with only the built-in local provider in place.
    External providers augment quality but are never required for correctness.

Reference: .providence/runtime analytics design §Phase 5
"""

from __future__ import annotations

from ._models import (
    AnalysisResult,
    BudgetEstimate,
    CompressedContext,
    ContextBundle,
    TaskContext,
)
from ._provider import (
    _BUDGET_MAX_BYTES,
    _BUDGET_MIN_BYTES,
    _COMPLEXITY_HIGH,
    _COMPLEXITY_LOW,
    _COMPLEXITY_MED,
    _LOCAL_CONFIDENCE,
    IntelligenceProvider,
    LocalIntelligenceProvider,
)
from ._registry import ProviderRegistry

__all__ = [
    "AnalysisResult",
    "BudgetEstimate",
    "CompressedContext",
    "ContextBundle",
    "IntelligenceProvider",
    "LocalIntelligenceProvider",
    "ProviderRegistry",
    "TaskContext",
    "_BUDGET_MAX_BYTES",
    "_BUDGET_MIN_BYTES",
    "_COMPLEXITY_HIGH",
    "_COMPLEXITY_LOW",
    "_COMPLEXITY_MED",
    "_LOCAL_CONFIDENCE",
]
