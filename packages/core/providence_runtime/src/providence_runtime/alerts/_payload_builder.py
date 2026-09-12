"""Webhook payload builders for AlertDispatcher."""

from __future__ import annotations

import os
from typing import Any


class _PayloadBuilderMixin:
    """Builds webhook payloads for the supported alert backends."""

    def _build_pagerduty_payload(self, event_dict: dict[str, Any]) -> dict[str, Any]:
        """PagerDuty Events API v2 trigger payload.

        Requires SDD_PD_ROUTING_KEY env var to be set.
        """
        routing_key = os.environ.get("SDD_PD_ROUTING_KEY", "").strip()
        if not routing_key:
            routing_key = "unknown-routing-key"

        agent_id = event_dict.get("agent_id", "unknown")
        event_type = event_dict.get("event", "unknown")
        budget_pct = event_dict.get("budget_utilization_pct", 0)
        path_id = event_dict.get("path_id", "")

        summary = f"SDD Budget Alert: {event_type}"
        if budget_pct:
            summary += f" ({budget_pct:.1f}%)"
        if path_id:
            summary += f" [PATH {path_id}]"

        severity = "critical" if "breach" in event_type else "warning"

        return {
            "routing_key": routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": summary,
                "severity": severity,
                "source": agent_id,
                "custom_details": {
                    "event": event_type,
                    "budget_utilization_pct": budget_pct,
                    "path_id": path_id,
                    "timestamp": event_dict.get("ts", ""),
                },
            },
        }

    def _build_slack_payload(self, event_dict: dict[str, Any]) -> dict[str, Any]:
        """Slack incoming webhook message payload."""
        agent_id = event_dict.get("agent_id", "unknown")
        event_type = event_dict.get("event", "unknown")
        budget_pct = event_dict.get("budget_utilization_pct", 0)
        path_id = event_dict.get("path_id", "")

        # Determine emoji and tone
        if "breach" in event_type:
            emoji = ":fire:"
            tone = "CRITICAL:"
        else:
            emoji = ":warning:"
            tone = "WARNING:"

        details = f"Agent: {agent_id}\nEvent: {event_type}"
        if budget_pct:
            details += f"\nBudget utilization: {budget_pct:.1f}%"
        if path_id:
            details += f"\nPath: {path_id}"

        text = f"{emoji} {tone} SDD Token Economy Alert\n{details}"

        return {"text": text}

    def _build_generic_payload(self, event_dict: dict[str, Any]) -> dict[str, Any]:
        """Plain JSON payload with event fields."""
        return event_dict
