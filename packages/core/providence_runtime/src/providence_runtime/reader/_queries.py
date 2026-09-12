"""Free-function query helpers operating on lists of raw event dicts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ._budget_status import BudgetStatus
from ._token_stats import TokenStats


def _filter_events_since(
    events: list[dict[str, Any]], last_hours: int
) -> list[dict[str, Any]]:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=last_hours)
    filtered = []
    for event in events:
        try:
            ts_str = event.get("ts", "")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts >= cutoff:
                    filtered.append(event)
        except ValueError:
            # Skip events with unparseable timestamps
            continue
    return filtered


def _token_stats(events: list[dict[str, Any]]) -> TokenStats:
    stats = TokenStats()
    for event in events:
        tokens_input = event.get("tokens_input") or 0
        tokens_output = event.get("tokens_output") or 0
        tokens_total = event.get("tokens_total") or 0

        stats.total_input_tokens += tokens_input
        stats.total_output_tokens += tokens_output
        stats.total_tokens += tokens_total
        stats.event_count += 1

        # Extract model from details
        details = event.get("details", {})
        if isinstance(details, dict):
            model = details.get("model", "unknown")
            stats.unique_models.add(model)
            cost = details.get("cost_usd", 0.0)
            stats.cost_usd += cost

    if stats.event_count > 0:
        stats.avg_tokens_per_event = stats.total_tokens / stats.event_count

    return stats


def _error_rate(events: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(events)
    if total == 0:
        return {
            "total_events": 0,
            "error_events": 0,
            "error_rate": 0.0,
            "error_types": {},
        }

    error_events = [e for e in events if e.get("status") == "fail"]
    error_count = len(error_events)

    # Aggregate error types
    error_types: dict[str, int] = {}
    for event in error_events:
        event_type = event.get("event", "unknown")
        error_types[event_type] = error_types.get(event_type, 0) + 1

    return {
        "total_events": total,
        "error_events": error_count,
        "error_rate": round(error_count / total * 100, 2) if total > 0 else 0.0,
        "error_types": error_types,
    }


def _budget_status(events: list[dict[str, Any]]) -> BudgetStatus:
    status = BudgetStatus()

    # Find the most recent budget event
    budget_events = [
        e for e in events if e.get("event", "").startswith("economy.budget")
    ]

    if not budget_events:
        return status

    # Use the most recent event
    latest = budget_events[-1]
    details = latest.get("details", {})

    if isinstance(details, dict):
        status.consumed_tokens = details.get("consumed", 0)
        status.max_tokens = details.get("limit", 0)
        status.consumed_cost_usd = details.get("consumed", 0.0)
        status.max_cost_usd = details.get("limit")

        if status.max_tokens > 0:
            status.utilization_pct = round(
                (status.consumed_tokens / status.max_tokens) * 100, 2
            )

        status.in_red_zone = status.utilization_pct >= status.warning_threshold_pct
        status.in_breach = status.utilization_pct >= status.breach_threshold_pct

    return status
