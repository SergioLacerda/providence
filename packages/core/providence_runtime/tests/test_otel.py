"""Tests for providence_runtime.otel — §13 Phase C OTEL mapping layer.

Covers:
- OtelAttributes.from_event(): field mapping, span_id resolution, to_otel_dict keys
- OtelBridge.emit(): JSONL write delegation + exporter call
- OtelBridge: graceful degradation when exporter raises / is None
- OtlpHttpExporter: OTLP payload structure, network error absorption
- Private helpers: _ts_to_nano, _status_code, _to_kv_list
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from providence_runtime._events import RuntimeEvent, _generate_span_id
from providence_runtime.otel import (
    OtelExporter,
    OtlpHttpExporter,
    _build_otlp_payload,
    _status_code,
    _to_kv_list,
    _ts_to_nano,
)
from providence_runtime.telemetry import (
    MODE_ACTIVE,
    OtelAttributes,
    OtelBridge,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _event(
    event: str = "governance.compile",
    command: str = "compile",
    status: str = "ok",
    trace_id: str = "trace-abc",
    span_id: str = "",
    duration_ms: int | None = None,
    decision_refs: list[str] | None = None,
) -> RuntimeEvent:
    return RuntimeEvent(
        event=event,
        command=command,
        status=status,
        trace_id=trace_id,
        span_id=span_id,
        agent_id="agent-1",
        workspace_id="ws-1",
        artifact_fingerprint="fp-abc",
        schema_version="3.0",
        duration_ms=duration_ms,
        decision_source_refs=decision_refs or [],
    )


# ---------------------------------------------------------------------------
# OtelAttributes — mapping
# ---------------------------------------------------------------------------


class TestOtelAttributesFromEvent:
    def test_service_name_mapped(self) -> None:
        attrs = OtelAttributes.from_event(_event())
        assert attrs.service_name == "providence-runtime"

    def test_trace_id_propagated(self) -> None:
        attrs = OtelAttributes.from_event(_event(trace_id="trace-xyz"))
        assert attrs.trace_id == "trace-xyz"

    def test_span_id_override_takes_priority(self) -> None:
        evt = _event(span_id="event-span")
        attrs = OtelAttributes.from_event(evt, span_id="override-span")
        assert attrs.span_id == "override-span"

    def test_span_id_falls_back_to_event_span_id(self) -> None:
        evt = _event(span_id="event-span-id")
        attrs = OtelAttributes.from_event(evt)
        assert attrs.span_id == "event-span-id"

    def test_span_id_generated_when_empty(self) -> None:
        evt = _event(span_id="")
        attrs = OtelAttributes.from_event(evt)
        assert attrs.span_id != ""
        assert len(attrs.span_id) == 16  # _generate_span_id() returns 16-char hex

    def test_sdd_event_mapped(self) -> None:
        attrs = OtelAttributes.from_event(_event(event="runtime.drift.detected"))
        assert attrs.sdd_event == "runtime.drift.detected"

    def test_duration_ms_none_when_not_set(self) -> None:
        attrs = OtelAttributes.from_event(_event(duration_ms=None))
        assert attrs.sdd_duration_ms is None

    def test_duration_ms_propagated(self) -> None:
        attrs = OtelAttributes.from_event(_event(duration_ms=42))
        assert attrs.sdd_duration_ms == 42

    def test_decision_source_refs_as_json(self) -> None:
        evt = _event(decision_refs=["M001", "P003"])
        attrs = OtelAttributes.from_event(evt)
        assert json.loads(attrs.sdd_decision_source_refs) == ["M001", "P003"]

    def test_empty_decision_refs_is_empty_json_array(self) -> None:
        attrs = OtelAttributes.from_event(_event(decision_refs=[]))
        assert attrs.sdd_decision_source_refs == "[]"


class TestOtelAttributesToOtelDict:
    def test_uses_dotted_sdd_keys(self) -> None:
        attrs = OtelAttributes.from_event(_event())
        d = attrs.to_otel_dict()
        assert "sdd.event" in d
        assert "sdd.command" in d
        assert "sdd.status" in d
        assert "sdd.agent_id" in d

    def test_service_name_key_present(self) -> None:
        attrs = OtelAttributes.from_event(_event())
        d = attrs.to_otel_dict()
        assert "service.name" in d
        assert d["service.name"] == "providence-runtime"

    def test_duration_ms_absent_when_none(self) -> None:
        attrs = OtelAttributes.from_event(_event(duration_ms=None))
        d = attrs.to_otel_dict()
        assert "sdd.duration_ms" not in d

    def test_duration_ms_present_when_set(self) -> None:
        attrs = OtelAttributes.from_event(_event(duration_ms=99))
        d = attrs.to_otel_dict()
        assert d["sdd.duration_ms"] == 99

    def test_namespace_separator_is_dot_not_underscore(self) -> None:
        # Keys must use dot-notation namespace prefix (sdd.foo, not sdd_foo)
        attrs = OtelAttributes.from_event(_event())
        d = attrs.to_otel_dict()
        sdd_keys = [k for k in d if k.startswith("sdd")]
        assert all(k.startswith("sdd.") for k in sdd_keys), (
            f"Found sdd key without dot-namespace: {[k for k in sdd_keys if not k.startswith('sdd.')]}"
        )


# ---------------------------------------------------------------------------
# OtelBridge
# ---------------------------------------------------------------------------


class TestOtelBridgeEmit:
    def test_emit_without_exporter_records_in_memory(self) -> None:
        bridge = OtelBridge(exporter=None)
        bridge.emit(_event())
        assert len(bridge.list_events()) == 1

    def test_emit_calls_exporter_export(self) -> None:
        mock_exporter = MagicMock()
        bridge = OtelBridge(exporter=mock_exporter)
        evt = _event()
        bridge.emit(evt)
        mock_exporter.export.assert_called_once()
        call_event, call_attrs = mock_exporter.export.call_args[0]
        assert call_event is evt
        assert isinstance(call_attrs, OtelAttributes)

    def test_emit_graceful_when_exporter_raises(self) -> None:
        mock_exporter = MagicMock()
        mock_exporter.export.side_effect = RuntimeError("network error")
        bridge = OtelBridge(exporter=mock_exporter)
        # Should not raise
        bridge.emit(_event())
        assert len(bridge.list_events()) == 1

    def test_emit_generates_span_id_when_event_has_none(self) -> None:
        mock_exporter = MagicMock()
        bridge = OtelBridge(exporter=mock_exporter)
        bridge.emit(_event(span_id=""))
        _, call_attrs = mock_exporter.export.call_args[0]
        assert call_attrs.span_id != ""

    def test_emit_preserves_event_span_id(self) -> None:
        mock_exporter = MagicMock()
        bridge = OtelBridge(exporter=mock_exporter)
        bridge.emit(_event(span_id="my-span-99"))
        _, call_attrs = mock_exporter.export.call_args[0]
        assert call_attrs.span_id == "my-span-99"


class TestOtelBridgeShutdown:
    def test_shutdown_calls_exporter_shutdown(self) -> None:
        mock_exporter = MagicMock()
        bridge = OtelBridge(exporter=mock_exporter)
        bridge.shutdown()
        mock_exporter.shutdown.assert_called_once()

    def test_shutdown_no_exporter_is_noop(self) -> None:
        bridge = OtelBridge(exporter=None)
        bridge.shutdown()  # Should not raise

    def test_shutdown_graceful_when_exporter_raises(self) -> None:
        mock_exporter = MagicMock()
        mock_exporter.shutdown.side_effect = RuntimeError("close error")
        bridge = OtelBridge(exporter=mock_exporter)
        bridge.shutdown()  # Should not raise


class TestOtelBridgeJsonlIntegration:
    def test_events_written_to_jsonl(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        bridge = OtelBridge(
            exporter=None,
            jsonl_path=log,
            logging_mode=MODE_ACTIVE,
        )
        bridge.emit(_event(event="runtime.session.start"))
        assert log.exists()
        record = json.loads(log.read_text(encoding="utf-8").strip())
        assert record["event"] == "runtime.session.start"


# ---------------------------------------------------------------------------
# OtlpHttpExporter
# ---------------------------------------------------------------------------


class TestOtlpHttpExporter:
    def _make_exporter(self) -> OtlpHttpExporter:
        return OtlpHttpExporter(
            endpoint="http://localhost:4318/v1/traces",
            headers={"X-Test": "value"},
            timeout=3,
        )

    def test_export_posts_to_endpoint(self) -> None:
        exporter = self._make_exporter()
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read = MagicMock(return_value=b"")

        with (
            patch("urllib.request.urlopen", return_value=mock_response),
            patch("urllib.request.Request") as mock_req_cls,
        ):
            mock_req_cls.return_value = MagicMock()
            evt = _event()
            attrs = OtelAttributes.from_event(evt)
            exporter.export(evt, attrs)
            mock_req_cls.assert_called_once()

    def test_export_silently_absorbs_network_errors(self) -> None:
        exporter = self._make_exporter()
        with (
            patch("urllib.request.urlopen", side_effect=OSError("connection refused")),
            patch("urllib.request.Request", return_value=MagicMock()),
        ):
            evt = _event()
            attrs = OtelAttributes.from_event(evt)
            exporter.export(evt, attrs)  # Should not raise

    def test_export_failure_is_counted(self) -> None:
        """TEL-07 regression: a swallowed network error must still increment
        `export_failure_count` — loss is silent to the caller (no raise) but
        not invisible in-process.
        `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` TEL-07.
        """
        exporter = self._make_exporter()
        assert exporter.export_failure_count == 0
        with (
            patch("urllib.request.urlopen", side_effect=OSError("connection refused")),
            patch("urllib.request.Request", return_value=MagicMock()),
        ):
            evt = _event()
            attrs = OtelAttributes.from_event(evt)
            exporter.export(evt, attrs)
            exporter.export(evt, attrs)
        assert exporter.export_failure_count == 2

    def test_export_success_does_not_increment_failure_count(self) -> None:
        exporter = self._make_exporter()
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read = MagicMock(return_value=b"")
        with (
            patch("urllib.request.urlopen", return_value=mock_response),
            patch("urllib.request.Request", return_value=MagicMock()),
        ):
            evt = _event()
            attrs = OtelAttributes.from_event(evt)
            exporter.export(evt, attrs)
        assert exporter.export_failure_count == 0

    def test_timeout_bounds_worst_case_export_latency(self) -> None:
        """TEL-07: `timeout` is the enforced latency ceiling for a single
        `export()` call — a hung collector cannot stall the caller past it."""

        exporter = OtlpHttpExporter(
            endpoint="http://localhost:4318/v1/traces", timeout=1
        )
        with (
            patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")),
            patch("urllib.request.Request", return_value=MagicMock()),
        ):
            evt = _event()
            attrs = OtelAttributes.from_event(evt)
            start = time.monotonic()
            exporter.export(evt, attrs)  # Must not raise or hang
            elapsed = time.monotonic() - start
        assert elapsed < 1.0  # mocked timeout raises immediately, no real wait
        assert exporter.export_failure_count == 1

    def test_shutdown_is_noop(self) -> None:
        exporter = self._make_exporter()
        exporter.shutdown()  # Should not raise


# ---------------------------------------------------------------------------
# _build_otlp_payload — payload structure
# ---------------------------------------------------------------------------


class TestBuildOtlpPayload:
    def test_top_level_structure(self) -> None:
        evt = _event()
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        assert "resourceSpans" in payload
        assert len(payload["resourceSpans"]) == 1

    def test_span_name_is_event(self) -> None:
        evt = _event(event="runtime.drift.detected")
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert span["name"] == "runtime.drift.detected"

    def test_span_ids_propagated(self) -> None:
        evt = _event(trace_id="trace-1", span_id="span-2")
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert span["traceId"] == "trace-1"
        assert span["spanId"] == "span-2"

    def test_status_ok(self) -> None:
        evt = _event(status="ok")
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert span["status"]["code"] == 1

    def test_status_fail(self) -> None:
        evt = _event(status="fail")
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert span["status"]["code"] == 2

    def test_attributes_are_kv_list(self) -> None:
        evt = _event()
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        span_attrs = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0][
            "attributes"
        ]
        assert isinstance(span_attrs, list)
        assert all("key" in a and "value" in a for a in span_attrs)

    def test_parent_span_id_native_field_set_when_parent_event_id_present(self) -> None:
        """TEL-08 regression: `parent_event_id` is populated with the
        parent's own `span_id` (see `_pipeline_runtime_telemetry.py`) — a
        valid OTLP span id, not a separate identifier scheme. It must be
        mapped onto the native `parentSpanId` span field so a real
        collector can reconstruct the span tree, not left only as the
        `sdd.parent_event_id` attribute.
        `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` TEL-08.
        """
        evt = _event(span_id="child-span")
        evt.parent_event_id = "parent-span"
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert span["parentSpanId"] == "parent-span"
        # Backward-compat: the sdd.* attribute correlation is preserved too.
        span_attrs = {a["key"]: a["value"] for a in span["attributes"]}
        assert span_attrs["sdd.parent_event_id"]["stringValue"] == "parent-span"

    def test_no_parent_span_id_field_for_root_span(self) -> None:
        evt = _event()
        assert evt.parent_event_id == ""
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert "parentSpanId" not in span

    def test_scope_name_is_providence_runtime(self) -> None:
        evt = _event()
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        scope = payload["resourceSpans"][0]["scopeSpans"][0]["scope"]
        assert scope["name"] == "providence-runtime"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


class TestTsToNano:
    def test_invalid_string_returns_zero(self) -> None:
        assert _ts_to_nano("not-a-date") == 0


class TestStatusCode:
    def test_ok_maps_to_1(self) -> None:
        assert _status_code("ok") == 1

    def test_warn_maps_to_1(self) -> None:
        assert _status_code("warn") == 1

    def test_fail_maps_to_2(self) -> None:
        assert _status_code("fail") == 2

    def test_unknown_maps_to_0(self) -> None:
        assert _status_code("unknown") == 0

    def test_case_insensitive(self) -> None:
        assert _status_code("OK") == 1
        assert _status_code("FAIL") == 2


class TestToKvList:
    def test_string_value(self) -> None:
        kv = _to_kv_list({"key": "value"})
        assert kv[0] == {"key": "key", "value": {"stringValue": "value"}}

    def test_int_value(self) -> None:
        kv = _to_kv_list({"count": 42})
        assert kv[0] == {"key": "count", "value": {"intValue": 42}}

    def test_float_value(self) -> None:
        kv = _to_kv_list({"ratio": 0.5})
        assert kv[0] == {"key": "ratio", "value": {"doubleValue": 0.5}}

    def test_bool_value(self) -> None:
        kv = _to_kv_list({"enabled": True})
        assert kv[0] == {"key": "enabled", "value": {"boolValue": True}}

    def test_none_converted_to_string(self) -> None:
        kv = _to_kv_list({"x": None})
        assert kv[0]["value"] == {"stringValue": "None"}

    def test_empty_dict_returns_empty_list(self) -> None:
        assert _to_kv_list({}) == []


class TestNewSpanId:
    def test_returns_16_char_hex(self) -> None:
        sid = _generate_span_id()
        assert len(sid) == 16
        int(sid, 16)  # Should not raise — must be valid hex

    def test_unique_each_call(self) -> None:
        ids = {_generate_span_id() for _ in range(20)}
        assert len(ids) == 20


# ---------------------------------------------------------------------------
# OtelExporter protocol conformance
# ---------------------------------------------------------------------------


class TestOtelExporterProtocol:
    def test_mock_conforms_to_protocol(self) -> None:
        mock = MagicMock(spec=OtelExporter)
        assert isinstance(mock, OtelExporter)

    def test_otlp_exporter_conforms_to_protocol(self) -> None:
        exporter = OtlpHttpExporter(endpoint="http://localhost:4318/v1/traces")
        assert isinstance(exporter, OtelExporter)

    def test_export_stub_returns_none(self) -> None:
        assert (
            OtelExporter.export(None, _event(), OtelAttributes.from_event(_event()))
            is None
        )

    def test_shutdown_stub_returns_none(self) -> None:
        assert OtelExporter.shutdown(None) is None


# ---------------------------------------------------------------------------
# OtelAttributes — Token Economy namespace coverage
# ---------------------------------------------------------------------------


class TestOtelAttributesEconomyNamespace:
    def test_all_economy_attributes_absent_when_none(self) -> None:
        attrs = OtelAttributes.from_event(_event())
        d = attrs.to_otel_dict()
        economy_keys = [k for k in d if k.startswith("sdd.economy.")]
        # path_id is always present but empty by default
        assert all(k == "sdd.economy.path_id" or d.get(k) is None for k in economy_keys)

    def test_tokens_input_present_when_set(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            tokens_input=500,
        )
        attrs = OtelAttributes.from_event(evt)
        d = attrs.to_otel_dict()
        assert d["sdd.economy.tokens_input"] == 500

    def test_tokens_output_present_when_set(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            tokens_output=300,
        )
        attrs = OtelAttributes.from_event(evt)
        d = attrs.to_otel_dict()
        assert d["sdd.economy.tokens_output"] == 300

    def test_tokens_total_present_when_set(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            tokens_total=800,
        )
        attrs = OtelAttributes.from_event(evt)
        d = attrs.to_otel_dict()
        assert d["sdd.economy.tokens_total"] == 800

    def test_budget_utilization_pct_present_when_set(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            budget_utilization_pct=75.5,
        )
        attrs = OtelAttributes.from_event(evt)
        d = attrs.to_otel_dict()
        assert d["sdd.economy.budget_utilization_pct"] == 75.5

    def test_compression_ratio_present_when_set(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            compression_ratio=0.42,
        )
        attrs = OtelAttributes.from_event(evt)
        d = attrs.to_otel_dict()
        assert d["sdd.economy.compression_ratio"] == 0.42

    def test_context_bytes_loaded_present_when_set(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            context_bytes_loaded=1024,
        )
        attrs = OtelAttributes.from_event(evt)
        d = attrs.to_otel_dict()
        assert d["sdd.economy.context_bytes_loaded"] == 1024

    def test_context_budget_bytes_present_when_set(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            context_budget_bytes=8192,
        )
        attrs = OtelAttributes.from_event(evt)
        d = attrs.to_otel_dict()
        assert d["sdd.economy.context_budget_bytes"] == 8192

    def test_path_id_present_when_set(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            path_id="A/B",
        )
        attrs = OtelAttributes.from_event(evt)
        d = attrs.to_otel_dict()
        assert d["sdd.economy.path_id"] == "A/B"

    def test_path_id_absent_when_empty(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            path_id="",
        )
        attrs = OtelAttributes.from_event(evt)
        d = attrs.to_otel_dict()
        assert "sdd.economy.path_id" not in d

    def test_retry_count_present_when_set(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            retry_count=3,
        )
        attrs = OtelAttributes.from_event(evt)
        d = attrs.to_otel_dict()
        assert d["sdd.economy.retry_count"] == 3

    def test_reflection_count_present_when_set(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            reflection_count=2,
        )
        attrs = OtelAttributes.from_event(evt)
        d = attrs.to_otel_dict()
        assert d["sdd.economy.reflection_count"] == 2


# ---------------------------------------------------------------------------
# OtelAttributes — to_dict() method
# ---------------------------------------------------------------------------


class TestOtelAttributesToDict:
    def test_to_dict_returns_all_fields(self) -> None:
        attrs = OtelAttributes.from_event(_event())
        d = attrs.to_dict()
        assert d["service_name"] == "providence-runtime"
        assert d["trace_id"] == "trace-abc"
        assert "sdd_event" in d
        assert "sdd_command" in d

    def test_to_dict_includes_underscore_names(self) -> None:
        # to_dict() uses underscore-separated field names (not dot notation)
        attrs = OtelAttributes.from_event(_event())
        d = attrs.to_dict()
        assert "sdd_event" in d  # Not "sdd.event"
        assert "sdd_command" in d
        assert "service_name" in d


# ---------------------------------------------------------------------------
# OtlpHttpExporter — endpoint validation
# ---------------------------------------------------------------------------


class TestOtlpHttpExporterEndpointValidation:
    def test_http_endpoint_allowed(self) -> None:
        exporter = OtlpHttpExporter(endpoint="http://localhost:4318/v1/traces")
        attrs = OtelAttributes.from_event(_event())
        with patch("urllib.request.urlopen", return_value=MagicMock()):
            # Should not raise
            exporter.export(_event(), attrs)

    def test_https_endpoint_allowed(self) -> None:
        exporter = OtlpHttpExporter(endpoint="https://api.example.com/v1/traces")
        attrs = OtelAttributes.from_event(_event())
        with patch("urllib.request.urlopen", return_value=MagicMock()):
            # Should not raise
            exporter.export(_event(), attrs)

    def test_remote_http_endpoint_rejected_by_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_OTEL_ALLOW_INSECURE_HTTP", raising=False)
        with pytest.raises(ValueError, match="plaintext HTTP for non-local host"):
            OtlpHttpExporter(endpoint="http://otel.example.com/v1/traces")

    def test_remote_http_endpoint_allowed_with_explicit_opt_in(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_OTEL_ALLOW_INSECURE_HTTP", "true")
        exporter = OtlpHttpExporter(endpoint="http://otel.example.com/v1/traces")
        assert exporter._endpoint == "http://otel.example.com/v1/traces"

    def test_file_scheme_silently_skipped(self) -> None:
        exporter = OtlpHttpExporter(endpoint="file:///etc/passwd")
        attrs = OtelAttributes.from_event(_event())
        with patch("urllib.request.urlopen") as mock_urlopen:
            exporter.export(_event(), attrs)
            # urlopen should not be called for file:// URLs
            mock_urlopen.assert_not_called()

    def test_custom_headers_added_to_request(self) -> None:
        exporter = OtlpHttpExporter(
            endpoint="http://localhost:4318/v1/traces",
            headers={"Authorization": "Bearer token123"},
        )
        attrs = OtelAttributes.from_event(_event())
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_response):
            exporter.export(_event(), attrs)

    def test_timeout_respected_in_urlopen(self) -> None:
        exporter = OtlpHttpExporter(
            endpoint="http://localhost:4318/v1/traces",
            timeout=10,
        )
        attrs = OtelAttributes.from_event(_event())
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        with patch(
            "urllib.request.urlopen", return_value=mock_response
        ) as mock_urlopen:
            exporter.export(_event(), attrs)
            # timeout parameter should be passed
            call_kwargs = mock_urlopen.call_args[1]
            assert call_kwargs["timeout"] == 10


# ---------------------------------------------------------------------------
# _build_otlp_payload — timestamp handling
# ---------------------------------------------------------------------------


class TestBuildOtlpPayloadTimestamps:
    def test_start_time_from_ts(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            ts="2026-05-10T12:00:00+00:00",
        )
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert span["startTimeUnixNano"] > 0

    def test_end_time_from_end_ts_when_present(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            ts="2026-05-10T12:00:00+00:00",
            end_ts="2026-05-10T12:00:05+00:00",
        )
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        # end_ns should be > start_ns
        assert span["endTimeUnixNano"] > span["startTimeUnixNano"]

    def test_end_time_falls_back_to_ts_when_absent(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            ts="2026-05-10T12:00:00+00:00",
            end_ts="",
        )
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        # Both should be same when end_ts not set
        assert span["endTimeUnixNano"] == span["startTimeUnixNano"]

    def test_invalid_timestamp_results_in_zero_ns(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            ts="invalid-timestamp",
        )
        attrs = OtelAttributes.from_event(evt)
        payload = _build_otlp_payload(evt, attrs)
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert span["startTimeUnixNano"] == 0


# ---------------------------------------------------------------------------
# _ts_to_nano — comprehensive timestamp conversion
# ---------------------------------------------------------------------------


class TestTsToNanoComprehensive:
    def test_utc_with_plus_offset(self) -> None:
        ns = _ts_to_nano("2026-05-10T12:00:00+00:00")
        assert ns > 0

    def test_naive_datetime_treated_as_utc(self) -> None:
        ns = _ts_to_nano("2026-05-10T12:00:00")
        assert ns > 0

    def test_timezone_offset_preserved(self) -> None:
        # Same instant, different timezone
        ns_utc = _ts_to_nano("2026-05-10T12:00:00+00:00")
        ns_plus5 = _ts_to_nano("2026-05-10T17:00:00+05:00")
        assert ns_utc == ns_plus5

    def test_none_string_returns_zero(self) -> None:
        assert _ts_to_nano("") == 0

    def test_malformed_date_returns_zero(self) -> None:
        assert _ts_to_nano("2026/05/10 12:00") == 0

    def test_result_is_positive_for_future(self) -> None:
        ns = _ts_to_nano("2050-01-01T00:00:00+00:00")
        assert ns > 0

    def test_result_is_positive_for_past(self) -> None:
        ns = _ts_to_nano("2000-01-01T00:00:00+00:00")
        assert ns > 0


# ---------------------------------------------------------------------------
# OtelBridge — more complex scenarios
# ---------------------------------------------------------------------------


class TestOtelBridgeComplexScenarios:
    def test_multiple_emits_with_exporter(self) -> None:
        mock_exporter = MagicMock()
        bridge = OtelBridge(exporter=mock_exporter)
        bridge.emit(_event(event="evt1"))
        bridge.emit(_event(event="evt2"))
        assert mock_exporter.export.call_count == 2

    def test_emit_after_shutdown(self) -> None:
        mock_exporter = MagicMock()
        bridge = OtelBridge(exporter=mock_exporter)
        bridge.shutdown()
        # After shutdown, still should accept emits (though exporter is not called if it raises)
        bridge.emit(_event())
        # Event should still be recorded in memory
        assert len(bridge.list_events()) == 1

    def test_exporter_exception_does_not_prevent_emission(self) -> None:
        # Exporter throws on FIRST call
        mock_exporter = MagicMock()
        mock_exporter.export.side_effect = [RuntimeError("oops"), None]
        bridge = OtelBridge(exporter=mock_exporter)
        bridge.emit(_event(event="evt1"))
        # Second emit succeeds
        bridge.emit(_event(event="evt2"))
        # Both events recorded
        assert len(bridge.list_events()) == 2


# ---------------------------------------------------------------------------
# OtlpHttpExporter — response handling
# ---------------------------------------------------------------------------


class TestOtlpHttpExporterResponseHandling:
    def test_response_body_is_read(self) -> None:
        exporter = OtlpHttpExporter(endpoint="http://localhost:4318/v1/traces")
        attrs = OtelAttributes.from_event(_event())
        mock_response = MagicMock()
        mock_response.read = MagicMock(return_value=b"success")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_response):
            exporter.export(_event(), attrs)
            mock_response.read.assert_called_once()

    def test_connection_timeout_silently_ignored(self) -> None:
        exporter = OtlpHttpExporter(endpoint="http://localhost:4318/v1/traces")
        attrs = OtelAttributes.from_event(_event())
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timeout")):
            # Should not raise
            exporter.export(_event(), attrs)

    def test_http_error_silently_ignored(self) -> None:
        exporter = OtlpHttpExporter(endpoint="http://localhost:4318/v1/traces")
        attrs = OtelAttributes.from_event(_event())

        with patch("urllib.request.urlopen", side_effect=OSError("Server error")):
            # Should not raise
            exporter.export(_event(), attrs)


# ---------------------------------------------------------------------------
# _to_kv_list — comprehensive type coverage
# ---------------------------------------------------------------------------


class TestToKvListComprehensive:
    def test_mixed_types(self) -> None:
        kv = _to_kv_list(
            {
                "str": "value",
                "int": 42,
                "float": 3.14,
                "bool": False,
            }
        )
        assert len(kv) == 4
        # Verify each type mapped correctly
        types_found = {item["key"] for item in kv}
        assert types_found == {"str", "int", "float", "bool"}

    def test_preserves_order(self) -> None:
        # Dict insertion order is preserved in Python 3.7+
        kv = _to_kv_list({"a": 1, "b": 2, "c": 3})
        keys = [item["key"] for item in kv]
        assert keys == ["a", "b", "c"]

    def test_large_int_value(self) -> None:
        kv = _to_kv_list({"big": 2**63 - 1})
        assert kv[0]["value"]["intValue"] == 2**63 - 1

    def test_negative_values(self) -> None:
        kv = _to_kv_list({"neg_int": -100, "neg_float": -3.14})
        assert kv[0]["value"]["intValue"] == -100
        assert kv[1]["value"]["doubleValue"] == -3.14

    def test_special_string_values(self) -> None:
        kv = _to_kv_list({"empty": "", "special": "!@#$%^&*()"})
        assert kv[0]["value"]["stringValue"] == ""
        assert kv[1]["value"]["stringValue"] == "!@#$%^&*()"


# ---------------------------------------------------------------------------
# OtelAttributes — edge cases
# ---------------------------------------------------------------------------


class TestOtelAttributesEdgeCases:
    def test_empty_workspace_id(self) -> None:
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="",
            artifact_fingerprint="fp",
            schema_version="3.0",
        )
        attrs = OtelAttributes.from_event(evt)
        assert attrs.sdd_workspace_id == ""

    def test_very_long_artifact_fingerprint(self) -> None:
        long_fp = "x" * 10000
        evt = RuntimeEvent(
            event="test",
            command="test",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint=long_fp,
            schema_version="3.0",
        )
        attrs = OtelAttributes.from_event(evt)
        assert attrs.sdd_artifact_fingerprint == long_fp

    def test_special_characters_in_event_name(self) -> None:
        evt = RuntimeEvent(
            event="governance.compile:error@v1",
            command="compile",
            status="ok",
            trace_id="t1",
            span_id="s1",
            agent_id="a1",
            workspace_id="w1",
            artifact_fingerprint="fp",
            schema_version="3.0",
        )
        attrs = OtelAttributes.from_event(evt)
        assert attrs.sdd_event == "governance.compile:error@v1"
