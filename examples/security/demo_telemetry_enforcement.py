#!/usr/bin/env python3
"""
SDD Security Demo — Telemetry Sink Enforcement (M007 / M009)

Shows two complementary telemetry enforcement patterns:

  1. AlertDispatcher — routes breach/cap events to a webhook endpoint,
     demonstrating that governance violations are observable externally.
     An operation that fires without a sink is "dark" (unauditable).

  2. TelemetrySink — captures all RuntimeEvents in-process (JSONL).
     Demonstrates that governance-sensitive calls (budget breach, retry cap)
     are recorded before any remediation path.

In production, operating without a configured sink violates M007
(Telemetry Enforcement) and M009 (OpenTelemetry Compliance).

Run from repo root:
    uv run python examples/security/demo_telemetry_enforcement.py
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from providence_runtime import RuntimeEvent, TelemetrySink
from providence_runtime.alerts import _DEFAULT_ALERT_EVENTS, AlertDispatcher

SECTION = "\n" + "=" * 60


# ── Scenario 1: AlertDispatcher intercepts a budget breach event ─────────


def demo_alert_dispatcher() -> None:
    print("\n[SDD] --- Scenario 1: AlertDispatcher intercepts breach events ---")

    # Wire a mock HTTP post so the demo works without a real endpoint.
    dispatcher = AlertDispatcher(
        url="https://hooks.example.com/sdd-alerts",
        webhook_type="generic",
    )

    captured_payloads: list[dict[str, Any]] = []

    def fake_post(payload: dict[str, Any]) -> None:
        captured_payloads.append(payload)

    with patch.object(dispatcher, "_post", side_effect=fake_post):
        # Non-breach event → silently ignored by the dispatcher
        normal_event = RuntimeEvent(
            event="task.completed",
            command="fix-typo",
            status="ok",
            trace_id="trace-001",
        )
        dispatcher.on_event(normal_event)

        # Budget breach event → dispatched to webhook
        breach_event = RuntimeEvent(
            event="economy.budget.breach.tokens",
            command="generate-report",
            status="fail",
            trace_id="trace-002",
            budget_utilization_pct=112.5,
            tokens_total=11250,
        )
        dispatcher.on_event(breach_event)

    print(f"[SDD] Monitored event types : {sorted(_DEFAULT_ALERT_EVENTS)}")
    print(f"[SDD] Events dispatched     : {len(captured_payloads)}")

    if captured_payloads:
        payload = captured_payloads[0]
        print("[SDD] Webhook payload (excerpt):")
        for k, v in list(payload.items())[:5]:
            print(f"[SDD]   {k}: {v}")
        print("[SDD] ✓ Breach event routed to incident webhook.")
    else:
        print("[SDD] No breach events were dispatched.")


# ── Scenario 2: TelemetrySink captures all events for audit ──────────────


def demo_sink_capture() -> None:
    print("\n[SDD] --- Scenario 2: TelemetrySink audit trail ---")

    sink = TelemetrySink()

    events_to_emit = [
        RuntimeEvent(
            event="session.start", command="bootstrap", status="ok", trace_id="t-1"
        ),
        RuntimeEvent(
            event="task.start", command="analyze", status="ok", trace_id="t-2"
        ),
        RuntimeEvent(
            event="economy.budget.breach",
            command="analyze",
            status="fail",
            trace_id="t-3",
            budget_utilization_pct=101.0,
        ),
        RuntimeEvent(
            event="economy.retry.cap.reached",
            command="analyze",
            status="fail",
            trace_id="t-4",
            retry_count=3,
        ),
    ]

    for evt in events_to_emit:
        sink.emit(evt)

    recorded = sink.list_events()
    print(f"[SDD] Events emitted   : {len(events_to_emit)}")
    print(f"[SDD] Events in sink   : {len(recorded)}")
    print("[SDD] Governance-sensitive events captured:")
    for evt in recorded:
        marker = "⚠" if "breach" in evt.event or "cap.reached" in evt.event else " "
        print(
            f"[SDD]   {marker} {evt.event}  trace={evt.trace_id}  status={evt.status}"
        )

    print("[SDD] ✓ Full audit trail preserved — operations are accountable.")


def main() -> None:
    print(SECTION)
    print("SDD Security — Telemetry Sink Enforcement Demo")
    print(SECTION)

    demo_alert_dispatcher()
    demo_sink_capture()

    print(SECTION)


if __name__ == "__main__":
    main()
