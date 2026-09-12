"""Factory function for Sink creation (Phase 1 Activation)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from ._constants import MODE_PASSIVE
from ._sink import TelemetrySink

logger: logging.Logger = logging.getLogger(__name__)

# Canonical OTLP endpoint env var (documented, preferred). SDD_OTEL_ENDPOINT is
# a legacy alias kept for CLI backward-compatibility — see get_otel_endpoint().
_OTEL_ENDPOINT_ENV = "SDD_OTEL_EXPORTER_ENDPOINT"
_OTEL_ENDPOINT_ENV_LEGACY = "SDD_OTEL_ENDPOINT"


def get_otel_endpoint() -> str:
    """Resolve the OTLP export endpoint from environment, in one place.

    Reads SDD_OTEL_EXPORTER_ENDPOINT (canonical). Falls back to the legacy
    SDD_OTEL_ENDPOINT alias — previously read independently by the CLI's
    ask_telemetry path — with a one-line deprecation warning, so both layers
    agree on which variable wins when a workspace sets both.
    """
    endpoint = os.environ.get(_OTEL_ENDPOINT_ENV, "").strip()
    if endpoint:
        return endpoint

    legacy_endpoint = os.environ.get(_OTEL_ENDPOINT_ENV_LEGACY, "").strip()
    if legacy_endpoint:
        logger.warning(
            "%s is deprecated; use %s instead",
            _OTEL_ENDPOINT_ENV_LEGACY,
            _OTEL_ENDPOINT_ENV,
        )
        return legacy_endpoint

    return ""


def create_sink(
    jsonl_path: Path | None = None,
    logging_mode: str = MODE_PASSIVE,
    segment_by_work_item: bool = False,
    agent_id: str | None = None,
) -> TelemetrySink:
    """Create a TelemetrySink or OtelBridge based on environment configuration.

    Activation via environment variables (resolved via get_otel_endpoint()):
      - SDD_OTEL_EXPORTER_ENDPOINT: Full OTLP HTTP endpoint (e.g., https://...)
        When set, returns OtelBridge; when unset, returns TelemetrySink.
      - SDD_OTEL_ENDPOINT: Deprecated alias for SDD_OTEL_EXPORTER_ENDPOINT.
      - SDD_OTEL_API_KEY: Optional API key header (e.g., for Datadog DD-API-KEY).
      - SDD_AGENT_ID: Agent identifier (fallback in TelemetrySink.__init__).
      - SDD_WEBHOOK_URL: Fase 2 — webhook destination for alert dispatch.
        When set, configures AlertDispatcher for event-triggered webhooks.

    Returns TelemetrySink (default) or OtelBridge (if endpoint is configured).

    Phase 1 implementation: Makes OTEL export opt-in via env var, preserving
    JSONL local-first semantics. OTEL is best-effort; JSONL is source of truth.

    Fase 2 implementation: Optionally wires AlertDispatcher for event-triggered
    webhook dispatch (best-effort side-car, all exceptions suppressed).
    """

    # Fase 2: Try to wire alert dispatcher from env
    alert_dispatcher = None
    try:
        from ..alerts import AlertDispatcher as AlertDispatcherClass

        alert_dispatcher = AlertDispatcherClass.from_env()
    except Exception:  # nosec B110 — intentional: alerts are optional, telemetry continues without them
        logger.debug(
            "Alert dispatcher unavailable; telemetry will continue without alerts",
            exc_info=True,
        )

    # Check if OTEL is configured
    otel_endpoint = get_otel_endpoint()

    # If no endpoint configured, return plain TelemetrySink with optional alert dispatcher
    if not otel_endpoint:
        return TelemetrySink(
            jsonl_path=jsonl_path,
            logging_mode=logging_mode,
            segment_by_work_item=segment_by_work_item,
            agent_id=agent_id,
            alert_dispatcher=alert_dispatcher,
        )

    # Endpoint is configured — use OtelBridge
    try:
        from ..otel import OtlpHttpExporter
        from . import OtelBridge

        # Prepare optional headers
        headers: dict[str, str] = {}
        api_key = os.environ.get("SDD_OTEL_API_KEY", "").strip()
        if api_key:
            # Auto-detect if endpoint looks like Datadog (use DD-API-KEY)
            parsed_url = urlparse(otel_endpoint)
            hostname = (parsed_url.hostname or "").lower()
            if hostname == "datadoghq.com" or hostname.endswith(".datadoghq.com"):
                headers["DD-API-KEY"] = api_key
            else:
                # Generic OTEL uses Authorization header
                headers["Authorization"] = f"Bearer {api_key}"

        exporter = OtlpHttpExporter(endpoint=otel_endpoint, headers=headers)
        sink = OtelBridge(
            exporter=exporter,
            jsonl_path=jsonl_path,
            logging_mode=logging_mode,
            segment_by_work_item=segment_by_work_item,
            agent_id=agent_id,
            alert_dispatcher=alert_dispatcher,
        )
        return sink
    except Exception as exc:
        # Fallback to plain TelemetrySink if OTel setup fails
        logger.warning(
            "Failed to initialize OTelBridge (%s); falling back to TelemetrySink", exc
        )
        return TelemetrySink(
            jsonl_path=jsonl_path,
            logging_mode=logging_mode,
            segment_by_work_item=segment_by_work_item,
            agent_id=agent_id,
            alert_dispatcher=alert_dispatcher,
        )
