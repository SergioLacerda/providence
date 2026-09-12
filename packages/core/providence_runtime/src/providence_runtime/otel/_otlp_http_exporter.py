"""OtlpHttpExporter — stdlib-only OTLP/JSON transport."""

from __future__ import annotations

import json
import os
from urllib.parse import urlparse

from .._events import OtelAttributes, RuntimeEvent
from ._payload import _build_otlp_payload

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class OtlpHttpExporter:
    """Export ``RuntimeEvent`` spans to any OTLP-HTTP/JSON endpoint.

    Supports Datadog (via ``/api/v0.2/traces``), Grafana, Jaeger, or any
    OpenTelemetry Collector with HTTP/JSON ingestion enabled.

    This exporter is intentionally minimal: it sends one span per event
    synchronously, uses stdlib ``urllib.request``, and swallows network
    errors rather than retrying or queueing. This is a deliberate scope
    boundary (TEL-07,
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`), not an
    oversight — a durable queue with batching and retry is a materially
    larger feature (background worker, backpressure policy, retry/backoff)
    that this stdlib-only, dependency-free exporter does not take on. For
    production use needing durable delivery, batching, or retry, wrap the
    official ``opentelemetry-exporter-otlp-proto-http`` package instead.

    What this exporter *does* guarantee, within that boundary:

    - **Bounded latency**: `timeout` caps each `export()` call's worst-case
      duration — a hung or slow collector cannot stall the caller past that
      ceiling (the "orçamento de latência" TEL-07 asks for).
    - **Loss is counted**: `export_failure_count` increments on every
      swallowed exception, so silent loss is at least observable in-process
      (not retried, not queued, but not invisible either).
    - **`shutdown()` is a deliberate no-op**: this exporter holds no
      persistent connection and no internal queue to flush — every
      `export()` call already completed (successfully or not) by the time
      it returns, so there is nothing pending at shutdown time.

    Parameters
    ----------
    endpoint:
        Full OTLP HTTP URL, e.g. ``https://otelcol.example.com:4318/v1/traces``.
    headers:
        Additional HTTP headers (e.g. ``{"DD-API-KEY": "..."}``)
    timeout:
        Socket timeout in seconds (default: 5) — the enforced worst-case
        latency ceiling for a single `export()` call.
    """

    def __init__(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        timeout: int = 5,
    ) -> None:
        self._validate_endpoint(endpoint)
        self._endpoint = endpoint
        self._headers = headers or {}
        self._timeout = timeout
        self._export_failure_count = 0

    @property
    def export_failure_count(self) -> int:
        """Count of `export()` calls that failed (network error or non-HTTP(S) skip).

        Not persisted or reset across process restarts — an in-process,
        best-effort loss counter (TEL-07's "perdas ... são contabilizados"),
        not a durable metric.
        """
        return self._export_failure_count

    @staticmethod
    def _validate_endpoint(endpoint: str) -> None:
        parsed = urlparse(endpoint)
        if parsed.scheme not in ("http", "https"):
            return
        hostname = parsed.hostname or ""
        is_local = hostname in _LOCAL_HOSTS
        allow_insecure = os.environ.get("SDD_OTEL_ALLOW_INSECURE_HTTP", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if parsed.scheme == "http" and not is_local and not allow_insecure:
            raise ValueError(
                f"OTLP endpoint uses plaintext HTTP for non-local host '{hostname}'. "
                "Use https:// for remote endpoints, or set "
                "SDD_OTEL_ALLOW_INSECURE_HTTP=true to explicitly opt in."
            )

    def export(self, event: RuntimeEvent, attrs: OtelAttributes) -> None:
        """POST a single OTLP-JSON span to the configured endpoint."""
        import urllib.request

        # Validate endpoint scheme (reject file:// and other unsafe schemes)
        parsed = urlparse(self._endpoint)
        if parsed.scheme not in ("http", "https"):
            self._export_failure_count += 1
            return  # Silently skip non-HTTP(S) endpoints

        payload = _build_otlp_payload(event, attrs)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self._endpoint, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        for key, value in self._headers.items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # nosec B310
                resp.read()
        except Exception:  # nosec B110 — best-effort OTEL delivery, failure is non-critical
            self._export_failure_count += 1

    def shutdown(self) -> None:
        """Deliberate no-op: no persistent connection or queue to flush.

        Every `export()` call is synchronous and already fully resolved
        (delivered or swallowed-and-counted) by the time it returns, so
        there is nothing pending here at shutdown time — see the class
        docstring's "shutdown()" note.
        """
