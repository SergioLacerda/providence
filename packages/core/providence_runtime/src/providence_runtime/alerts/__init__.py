"""Alert webhooks for token economy events.

Zero-dependency: stdlib urllib.request only. Activation via env vars:

  SDD_WEBHOOK_URL      — destination URL (required to enable alerts)
                         HTTPS required by default; set SDD_WEBHOOK_ALLOW_HTTP=true to allow HTTP
  SDD_WEBHOOK_TYPE     — pagerduty | slack | generic (default: generic)
  SDD_WEBHOOK_EVENTS   — comma-separated event names to fire on
                         (default: economy.budget.breach,economy.retry.cap.reached)
  SDD_WEBHOOK_TIMEOUT  — HTTP timeout in seconds (default: 5)
  SDD_PD_ROUTING_KEY   — PagerDuty Events API v2 routing key (required for type=pagerduty)
  SDD_WEBHOOK_ALLOW_HTTP — set to 'true' to allow plain HTTP (not recommended for production)

Usage::

    from providence_runtime.alerts import AlertDispatcher

    # From environment (preferred for production)
    dispatcher = AlertDispatcher.from_env()
    if dispatcher:
        dispatcher.on_event(runtime_event)

    # Or explicit construction
    dispatcher = AlertDispatcher(
        url="https://events.pagerduty.com/v2/enqueue",
        webhook_type="pagerduty",
        events=frozenset({"economy.budget.breach"}),
    )
    dispatcher.on_event(event)

The dispatcher is designed as a best-effort side-car in TelemetrySink.emit():
all network errors and malformed payloads are silently suppressed.
"""

from __future__ import annotations

from ._dispatcher import _DEFAULT_ALERT_EVENTS, AlertDispatcher
from ._payload_builder import _PayloadBuilderMixin

__all__ = [
    "_DEFAULT_ALERT_EVENTS",
    "AlertDispatcher",
    "_PayloadBuilderMixin",
]
