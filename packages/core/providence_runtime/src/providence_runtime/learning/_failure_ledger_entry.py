"""FailureLedgerEntry — a single recorded failure for supervised learning."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FailureLedgerEntry:
    """FailureLedgerEntry."""

    symptom: str
    root_cause: str
    fix: str
    validation: str
    regression: bool
    tags: list[str]
    evidence_refs: list[str]
    timestamp: str
