"""Derived economy-field enrichment for RuntimeEvent before persistence."""

from __future__ import annotations

from .._events import RuntimeEvent
from ._constants import _PATH_BUDGET_BYTES


def _enrich_economy(event: RuntimeEvent) -> None:
    """Auto-populate derived economy fields when source data is available.

    Mutates *event* in place before it is appended to the in-memory list
    and written to the JSONL sink.  All derivations are idempotent — a
    field that is already set is never overwritten.
    """
    # 1. Derive context_budget_bytes from path_id when not explicitly set.
    if event.context_budget_bytes is None and event.path_id in _PATH_BUDGET_BYTES:
        event.context_budget_bytes = _PATH_BUDGET_BYTES[event.path_id]

    # 2. Compute budget_utilization_pct from byte counts.
    if (
        event.budget_utilization_pct is None
        and event.context_bytes_loaded is not None
        and event.context_budget_bytes is not None
        and event.context_budget_bytes > 0
    ):
        event.budget_utilization_pct = round(
            event.context_bytes_loaded / event.context_budget_bytes * 100, 2
        )

    # 3. Compute tokens_total from input + output when not set.
    if (
        event.tokens_total is None
        and event.tokens_input is not None
        and event.tokens_output is not None
    ):
        event.tokens_total = event.tokens_input + event.tokens_output
