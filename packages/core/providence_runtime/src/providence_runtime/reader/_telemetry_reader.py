"""TelemetryReader — Query interface for runtime events (Phase 1 implementation)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._budget_status import BudgetStatus
from ._queries import _budget_status, _error_rate, _filter_events_since, _token_stats
from ._token_stats import TokenStats


class TelemetryReader:
    """Local query interface for runtime event JSONL files.

    Phase 1 implementation provides basic filtering, aggregation, and summaries.
    All operations are in-memory; suitable for single-session analysis.

    Parameters
    ----------
    jsonl_path:
        Path to the JSONL event file (e.g., ``.providence/runtime/events.jsonl``).
        If the file does not exist, operations return empty results gracefully.
    """

    def __init__(self, jsonl_path: Path) -> None:
        self._path = jsonl_path
        self._events: list[dict[str, Any]] = []
        self._load_events()

    def _load_events(self) -> None:
        """Load all events from the JSONL file into memory."""
        if not self._path.exists():
            return

        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            self._events.append(json.loads(line))
                        except json.JSONDecodeError:
                            # Skip malformed lines
                            continue
        except Exception:  # nosec B110
            # Gracefully handle read errors
            pass

    def get_events_by_type(
        self, event_type: str, last_hours: int | None = None
    ) -> list[dict[str, Any]]:
        """Get events of a specific type, optionally filtered by time window.

        Parameters
        ----------
        event_type:
            Event type to filter by (e.g., "economy.token.consume").
        last_hours:
            If provided, only return events from the last N hours.

        Returns
        -------
        List of matching events (empty if none found).
        """
        matching = [e for e in self._events if e.get("event") == event_type]

        if last_hours is None:
            return matching

        return _filter_events_since(matching, last_hours)

    def get_token_stats(self, last_hours: int | None = None) -> TokenStats:
        """Aggregate token consumption statistics across all economy.token.consume events.

        Parameters
        ----------
        last_hours:
            If provided, only analyze events from the last N hours.

        Returns
        -------
        TokenStats object with aggregated totals and summaries.
        """
        events = self.get_events_by_type("economy.token.consume", last_hours)
        return _token_stats(events)

    def get_error_rate(self, last_hours: int | None = None) -> dict[str, Any]:
        """Compute error rate across all events.

        Parameters
        ----------
        last_hours:
            If provided, only analyze events from the last N hours.

        Returns
        -------
        Dict with error statistics: {total_events, error_events, error_rate, error_types}.
        """
        events = (
            _filter_events_since(self._events, last_hours)
            if last_hours is not None
            else self._events
        )
        return _error_rate(events)

    def get_budget_status(self) -> BudgetStatus:
        """Get current budget status from the most recent economy.budget.* events.

        Returns
        -------
        BudgetStatus snapshot based on latest available data.
        """
        return _budget_status(self._events)

    def get_events_by_agent(self, agent_id: str) -> list[dict[str, Any]]:
        """Get all events from a specific agent.

        Parameters
        ----------
        agent_id:
            Agent ID to filter by.

        Returns
        -------
        List of events from the specified agent.
        """
        return [e for e in self._events if e.get("agent_id") == agent_id]

    def get_events_by_status(self, status: str) -> list[dict[str, Any]]:
        """Get all events with a specific status (ok, warn, fail).

        Parameters
        ----------
        status:
            Status value to filter by (ok, warn, fail).

        Returns
        -------
        List of events with the specified status.
        """
        return [e for e in self._events if e.get("status") == status]

    def get_latest_events(self, n: int = 50) -> list[dict[str, Any]]:
        """Get the N most recent events.

        Parameters
        ----------
        n:
            Number of recent events to return.

        Returns
        -------
        List of the N most recent events (empty if fewer than N exist).
        """
        return self._events[-n:] if self._events else []

    def get_event_count(self) -> int:
        """Return total count of loaded events."""
        return len(self._events)

    def list_events(self) -> list[dict[str, Any]]:
        """Return all loaded events as a list of dicts.

        Returns
        -------
        All events from the JSONL file (empty list if file does not exist).
        """
        return list(self._events)

    def clear_cache(self) -> None:
        """Reload events from disk (useful if file was updated externally)."""
        self._events = []
        self._load_events()
