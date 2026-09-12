"""A single normalised governance item from a compiled artifact."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GovernanceItem:
    """A single normalised governance item from a compiled artifact."""

    id: str
    title: str
    item_type: str  # MANDATE | POLICY | GUIDELINE | UNKNOWN
    description: str = ""
    rationale: str = ""
    summary_minimal: str = ""
    summary_runtime: str = ""
    summary_full: str = ""
    criticality: str = ""
