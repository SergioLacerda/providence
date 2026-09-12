"""Data types exchanged with intelligence providers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaskContext:
    """Input to :meth:`IntelligenceProvider.analyze_task` and
    :meth:`IntelligenceProvider.estimate_budget`.

    Attributes
    ----------
    query:
        Task description or user instruction text.
    path_id:
        Active PATH classification ("A" | "B" | "C" | "D"); empty when not
        yet classified.
    context_bytes_loaded:
        Bytes already loaded into the context window, if known.
    context_budget_bytes:
        Total context budget ceiling for the current PATH, if known.
    """

    query: str
    path_id: str = ""
    context_bytes_loaded: int | None = None
    context_budget_bytes: int | None = None


@dataclass
class AnalysisResult:
    """Output of :meth:`IntelligenceProvider.analyze_task`.

    Attributes
    ----------
    task_class:
        Detected task category: ``"bug-fix"``, ``"feature"``, ``"refactor"``,
        ``"test"``, ``"docs"``, or ``"unknown"``.
    complexity_score:
        Estimated complexity in the range 0.0–1.0.
    suggested_path_id:
        Recommended PATH based on task class and complexity.
    keywords:
        Matched keywords that drove the classification (deduplicated).
    provider:
        Name of the provider that produced this result.
    """

    task_class: str
    complexity_score: float
    suggested_path_id: str
    keywords: list[str]
    provider: str


@dataclass
class ContextBundle:
    """Input to :meth:`IntelligenceProvider.compress_context`.

    Attributes
    ----------
    items:
        Raw context strings to compress.
    query:
        The query these items were loaded for (used by semantic providers).
    budget_bytes:
        Target size in bytes after compression.
    """

    items: list[str]
    query: str
    budget_bytes: int


@dataclass
class CompressedContext:
    """Output of :meth:`IntelligenceProvider.compress_context`.

    Attributes
    ----------
    items:
        Compressed context strings.
    original_bytes:
        Total UTF-8 bytes of the input items.
    compressed_bytes:
        Total UTF-8 bytes of the output items.
    compression_ratio:
        ``compressed_bytes / original_bytes``; 1.0 means no reduction.
    provider:
        Name of the provider that produced this result.
    """

    items: list[str]
    original_bytes: int
    compressed_bytes: int
    compression_ratio: float
    provider: str


@dataclass
class BudgetEstimate:
    """Output of :meth:`IntelligenceProvider.estimate_budget`.

    Attributes
    ----------
    estimated_bytes:
        Predicted context bytes required for the task.
    suggested_path_id:
        PATH that best fits the estimated size.
    confidence:
        Estimate confidence in range 0.0–1.0.
    provider:
        Name of the provider that produced this result.
    """

    estimated_bytes: int
    suggested_path_id: str
    confidence: float
    provider: str
