"""AlertDispatcher — routes RuntimeEvents to configured webhook targets."""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from ._payload_builder import _PayloadBuilderMixin

logger = logging.getLogger("providence_runtime.alerts")

if TYPE_CHECKING:
    from .._events import RuntimeEvent

# Default events that trigger alert dispatch
_DEFAULT_ALERT_EVENTS = frozenset(
    {
        "economy.budget.breach",
        "economy.budget.breach.tokens",
        "economy.budget.breach.usd",
        "economy.retry.cap.reached",
    }
)


class AlertDispatcher(_PayloadBuilderMixin):
    """Routes RuntimeEvents to configured webhook targets.

    Designed for use as a best-effort side-car in TelemetrySink.emit():

    ::

        if self._alert_dispatcher is not None:
            with contextlib.suppress(Exception):
                self._alert_dispatcher.on_event(event)

    All network errors and malformed payloads are silently suppressed.

    Parameters
    ----------
    url:
        Webhook destination URL. Must be http or https.
    webhook_type:
        "pagerduty" | "slack" | "generic" (default: "generic").
        Determines payload format and headers.
    events:
        Set of event names that trigger dispatch. Defaults to breach + retry cap events.
    timeout:
        HTTP socket timeout in seconds (default: 5).
    """

    def __init__(
        self,
        url: str,
        webhook_type: str = "generic",
        events: frozenset[str] | None = None,
        timeout: int = 5,
        allow_http: bool = False,
    ) -> None:
        parsed = urlparse(url)
        if parsed.scheme == "http" and not allow_http:
            raise ValueError(
                "HTTP webhooks are not secure. Use HTTPS or set allow_http=True. "
                "For production, always use HTTPS with valid certificates."
            )
        self._url = url
        self._webhook_type = webhook_type
        self._events = events or _DEFAULT_ALERT_EVENTS
        self._timeout = timeout

    def on_event(self, event: RuntimeEvent | dict[str, Any]) -> None:
        """Dispatch alert if event matches the configured trigger set. Best-effort.

        Parameters
        ----------
        event:
            A RuntimeEvent or dict representation. Must have field: event (str).
        """
        # Normalize to dict interface
        event_dict = event.to_dict() if hasattr(event, "to_dict") else event

        event_type = event_dict.get("event", "")

        # Check if this event type matches the trigger set
        if event_type not in self._events:
            return

        # Build and dispatch payload
        if self._webhook_type == "pagerduty":
            payload = self._build_pagerduty_payload(event_dict)
        elif self._webhook_type == "slack":
            payload = self._build_slack_payload(event_dict)
        else:  # generic
            payload = self._build_generic_payload(event_dict)

        self._post(payload)

    @classmethod
    def from_env(cls) -> AlertDispatcher | None:
        """Build from SDD_WEBHOOK_* env vars. Returns None if SDD_WEBHOOK_URL is unset.

        Returns
        -------
        AlertDispatcher if SDD_WEBHOOK_URL is configured, else None.
        """
        url = os.environ.get("SDD_WEBHOOK_URL", "").strip()
        if not url:
            return None

        webhook_type = os.environ.get("SDD_WEBHOOK_TYPE", "generic").strip()
        timeout = int(os.environ.get("SDD_WEBHOOK_TIMEOUT", "5"))
        allow_http = os.environ.get("SDD_WEBHOOK_ALLOW_HTTP", "").lower() == "true"

        # Parse event names
        events_str = os.environ.get(
            "SDD_WEBHOOK_EVENTS",
            "economy.budget.breach,economy.budget.breach.tokens,economy.budget.breach.usd,economy.retry.cap.reached",
        ).strip()
        events = frozenset(e.strip() for e in events_str.split(",") if e.strip())

        return cls(
            url=url,
            webhook_type=webhook_type,
            events=events,
            timeout=timeout,
            allow_http=allow_http,
        )

    def _post(self, payload: dict[str, Any]) -> None:
        """HTTP POST via stdlib urllib.request. All errors suppressed.

        Follows the exact pattern from OtlpHttpExporter.export():
        - Validates endpoint scheme (HTTPS required unless explicitly allowed)
        - Sets Content-Type: application/json
        - Uses stdlib urllib.request with configurable timeout
        - Swallows all exceptions silently (best-effort delivery)

        Parameters
        ----------
        payload:
            Dict to serialize as JSON and POST.
        """
        import urllib.request

        # Validate endpoint scheme (reject file:// and other unsafe schemes)
        parsed = urlparse(self._url)
        if parsed.scheme not in ("http", "https"):
            return  # Silently skip non-HTTP(S) endpoints

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self._url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # nosec B310
                resp.read()
        except Exception as exc:  # nosec B110 — best-effort alert delivery
            logger.warning("alert dispatch failed (best-effort): %s", exc)
