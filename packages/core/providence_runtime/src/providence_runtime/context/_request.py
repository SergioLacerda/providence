"""ContextRequest — specification for a context loading request."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..artifacts import CompiledArtifact


@dataclass
class ContextRequest:
    """Specification for a context loading request."""

    query: str
    max_items: int = 5
    artifact: CompiledArtifact | None = None
    item_types: list[str] = field(default_factory=list)  # filter by type if non-empty
    budget_utilization_pct: float | None = (
        None  # current utilization; ≥100 → BREACH block
    )
    prefer_full_summary: bool = (
        False  # if True, GREEN zone prefers summary_full when available
    )
