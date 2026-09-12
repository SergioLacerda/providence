from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from providence_runtime import RuntimeEvent
from providence_runtime.telemetry import (
    MODE_ACTIVE,
    MODE_PASSIVE,
    TelemetrySink,
    create_sink,
)


class _FailingAlertDispatcher:
    def on_event(self, _event: RuntimeEvent) -> None:
        raise RuntimeError("boom")


def test_emit_suppresses_alert_dispatcher_errors() -> None:
    sink = TelemetrySink(
        logging_mode=MODE_ACTIVE, alert_dispatcher=_FailingAlertDispatcher()
    )
    sink.emit(
        RuntimeEvent(
            event="runtime.session.start", command="runtime", status="ok", trace_id="t1"
        )
    )
    assert len(sink.list_events()) == 1


def test_create_sink_returns_plain_sink_without_endpoint() -> None:
    with patch.dict(os.environ, {"SDD_OTEL_EXPORTER_ENDPOINT": ""}, clear=False):
        sink = create_sink(logging_mode=MODE_ACTIVE)
        assert isinstance(sink, TelemetrySink)


def test_create_sink_falls_back_when_exporter_init_fails() -> None:
    with (
        patch.dict(
            os.environ,
            {"SDD_OTEL_EXPORTER_ENDPOINT": "https://example.com/v1/traces"},
            clear=False,
        ),
        patch(
            "providence_runtime.telemetry.OtlpHttpExporter",
            side_effect=RuntimeError("no exporter"),
            create=True,
        ),
    ):
        sink = create_sink(logging_mode=MODE_ACTIVE)
        assert isinstance(sink, TelemetrySink)


def test_create_sink_builds_datadog_header() -> None:
    captured: dict[str, Any] = {}

    class _Exporter:
        def __init__(self, endpoint: str, headers: dict[str, str]) -> None:
            captured["endpoint"] = endpoint
            captured["headers"] = headers

    class _Bridge(TelemetrySink):
        def __init__(self, exporter: Any, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.exporter = exporter

    with (
        patch.dict(
            os.environ,
            {
                "SDD_OTEL_EXPORTER_ENDPOINT": "https://trace.agent.datadoghq.com/v1/traces",
                "SDD_OTEL_API_KEY": "k1",
            },
            clear=False,
        ),
        patch("providence_runtime.otel.OtlpHttpExporter", _Exporter),
        patch("providence_runtime.telemetry.OtelBridge", _Bridge, create=True),
    ):
        sink = create_sink(logging_mode=MODE_ACTIVE)
        assert isinstance(sink, _Bridge)
        assert captured["headers"]["DD-API-KEY"] == "k1"


def test_create_sink_builds_generic_bearer_header() -> None:
    captured: dict[str, Any] = {}

    class _Exporter:
        def __init__(self, endpoint: str, headers: dict[str, str]) -> None:
            captured["endpoint"] = endpoint
            captured["headers"] = headers

    class _Bridge(TelemetrySink):
        def __init__(self, exporter: Any, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.exporter = exporter

    with (
        patch.dict(
            os.environ,
            {
                "SDD_OTEL_EXPORTER_ENDPOINT": "https://otel.example.com/v1/traces",
                "SDD_OTEL_API_KEY": "k2",
            },
            clear=False,
        ),
        patch("providence_runtime.otel.OtlpHttpExporter", _Exporter),
        patch("providence_runtime.telemetry.OtelBridge", _Bridge, create=True),
    ):
        sink = create_sink(logging_mode=MODE_ACTIVE)
        assert isinstance(sink, _Bridge)
        assert captured["headers"]["Authorization"] == "Bearer k2"


def test_flush_writes_events_to_jsonl() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "events.jsonl"
        sink = TelemetrySink(jsonl_path=path, logging_mode=MODE_ACTIVE)
        sink.emit(
            RuntimeEvent(
                event="runtime.session.start",
                command="runtime",
                status="ok",
                trace_id="t1",
            )
        )
        sink.flush()
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 1


def test_flush_after_emit_does_not_duplicate_active_mode() -> None:
    """`emit()` already persists in active mode; a later `flush()` must not
    re-write the same event."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "events.jsonl"
        sink = TelemetrySink(jsonl_path=path, logging_mode=MODE_ACTIVE)
        sink.emit(
            RuntimeEvent(
                event="runtime.session.start",
                command="runtime",
                status="ok",
                trace_id="t1",
            )
        )
        sink.flush()
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1


def test_flush_after_emit_does_not_duplicate_passive_mandatory_event() -> None:
    """`governance.ask` is mandatory and persisted immediately even in passive
    mode; `enqueue_flush` must not write it a second time."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "events.jsonl"
        sink = TelemetrySink(jsonl_path=path, logging_mode=MODE_PASSIVE)
        sink.emit(
            RuntimeEvent(
                event="governance.ask",
                command="ask",
                status="ok",
                trace_id="t1",
            )
        )
        sink.flush()
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
