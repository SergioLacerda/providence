"""TelemetryReader — Query interface for runtime events (Phase 1 implementation).

Provides local ad-hoc queries over JSONL event files without requiring Python REPL.
Supports filtering by event type, time window, status, and aggregation of token economy.

Usage::

    from providence_runtime.reader import TelemetryReader
    from pathlib import Path

    reader = TelemetryReader(Path(".providence/runtime/events.jsonl"))

    # Get recent events of a specific type
    events = reader.get_events_by_type("economy.token.consume", last_hours=24)

    # Token consumption summary
    summary = reader.get_token_stats()

    # Error rate analysis
    error_rate = reader.get_error_rate()

    # Budget status
    budget = reader.get_budget_status()
"""

from __future__ import annotations

from ._budget_status import BudgetStatus
from ._telemetry_reader import TelemetryReader
from ._token_stats import TokenStats

__all__ = [
    "BudgetStatus",
    "TelemetryReader",
    "TokenStats",
]
