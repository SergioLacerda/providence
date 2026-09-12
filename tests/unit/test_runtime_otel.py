from types import SimpleNamespace

from providence_runtime._events import _generate_span_id
from providence_runtime.otel import (
    _build_otlp_payload,
    _status_code,
    _to_kv_list,
    _ts_to_nano,
)
from providence_runtime.telemetry import OtelAttributes, OtelBridge


class DummyExporter:
    def __init__(self):
        self.exported = []
        self.shutdown_called = False

    def export(self, event, attrs):
        self.exported.append((event, attrs))

    def shutdown(self):
        self.shutdown_called = True


def test_generate_span_id_is_hex():
    sid = _generate_span_id()
    assert isinstance(sid, str)
    assert len(sid) == 16
    int(sid, 16)


def test_ts_to_nano_valid_and_invalid():
    assert _ts_to_nano("2024-01-01T00:00:00+00:00") > 0
    assert _ts_to_nano("") == 0
    assert _ts_to_nano("not-a-date") == 0


def test_status_code_mapping():
    assert _status_code("ok") == 1
    assert _status_code("warn") == 1
    assert _status_code("fail") == 2
    assert _status_code("other") == 0


def test_to_kv_list_types():
    d = {"a": True, "b": 1, "c": 1.5, "d": "x"}
    kv = _to_kv_list(d)
    assert any(x["value"].get("boolValue") is True for x in kv)
    assert any(x["value"].get("intValue") == 1 for x in kv)
    assert any(x["value"].get("doubleValue") == 1.5 for x in kv)
    assert any(x["value"].get("stringValue") == "x" for x in kv)


def test_build_otlp_payload_structure():
    event = SimpleNamespace(
        service="svc",
        trace_id="trace",
        span_id="span",
        parent_event_id="",
        event="evt",
        command="cmd",
        status="ok",
        level="INFO",
        workspace_id="ws",
        agent_id="agent",
        artifact_fingerprint="fp",
        schema_version="1.0",
        event_schema_version="1.0",
        decision_source_refs=["M001"],
        duration_ms=123,
        tokens_input=10,
        tokens_output=20,
        tokens_total=30,
        context_bytes_loaded=100,
        context_budget_bytes=200,
        budget_utilization_pct=50.0,
        compression_ratio=0.8,
        retry_count=1,
        reflection_count=2,
        path_id="A",
        ts="2024-01-01T00:00:00+00:00",
        end_ts="2024-01-01T00:00:01+00:00",
    )
    attrs = OtelAttributes.from_event(event)
    payload = _build_otlp_payload(event, attrs)
    assert "resourceSpans" in payload
    rs = payload["resourceSpans"][0]
    assert "resource" in rs
    assert "scopeSpans" in rs
    span = rs["scopeSpans"][0]["spans"][0]
    assert span["traceId"] == attrs.trace_id
    assert span["spanId"] == attrs.span_id
    assert span["name"] == attrs.sdd_event
    assert span["kind"] == 1
    assert span["attributes"]
    assert span["status"]["code"] == 1


def test_ot_bridge_emits_and_exports(tmp_path):
    exporter = DummyExporter()
    sink = OtelBridge(exporter=exporter, jsonl_path=tmp_path / "events.jsonl")
    event = SimpleNamespace(
        service="svc",
        trace_id="trace",
        span_id="span",
        parent_event_id="",
        event="evt",
        command="cmd",
        status="ok",
        level="INFO",
        workspace_id="ws",
        agent_id="agent",
        artifact_fingerprint="fp",
        schema_version="1.0",
        event_schema_version="1.0",
        decision_source_refs=["M001"],
        duration_ms=123,
        tokens_input=10,
        tokens_output=20,
        tokens_total=30,
        context_bytes_loaded=100,
        context_budget_bytes=200,
        budget_utilization_pct=50.0,
        compression_ratio=0.8,
        retry_count=1,
        reflection_count=2,
        path_id="A",
        ts="2024-01-01T00:00:00+00:00",
        end_ts="2024-01-01T00:00:01+00:00",
    )
    sink.emit(event)
    assert exporter.exported
    sink.shutdown()
    assert exporter.shutdown_called


def test_ot_bridge_no_exporter(tmp_path):
    sink = OtelBridge(exporter=None, jsonl_path=tmp_path / "events.jsonl")
    event = SimpleNamespace(
        service="svc",
        trace_id="trace",
        span_id="span",
        parent_event_id="",
        event="evt",
        command="cmd",
        status="ok",
        level="INFO",
        workspace_id="ws",
        agent_id="agent",
        artifact_fingerprint="fp",
        schema_version="1.0",
        event_schema_version="1.0",
        decision_source_refs=["M001"],
        duration_ms=123,
        tokens_input=10,
        tokens_output=20,
        tokens_total=30,
        context_bytes_loaded=100,
        context_budget_bytes=200,
        budget_utilization_pct=50.0,
        compression_ratio=0.8,
        retry_count=1,
        reflection_count=2,
        path_id="A",
        ts="2024-01-01T00:00:00+00:00",
        end_ts="2024-01-01T00:00:01+00:00",
    )
    sink.emit(event)  # Should not raise
    sink.shutdown()  # Should not raise


def test_otlp_http_exporter_makes_post(monkeypatch):
    from providence_runtime.otel import OtlpHttpExporter

    called = {}

    def fake_urlopen(req, timeout=None):
        called["url"] = req.full_url
        called["data"] = req.data
        # header_items() returns list of tuples; convert to dict with proper casing
        called["headers"] = {k.lower(): v for k, v in req.header_items()}

        class DummyResp:
            def read(self):
                return b""

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return DummyResp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    exporter = OtlpHttpExporter(endpoint="https://fake-endpoint")

    class DummyEvent:
        ts = "2024-01-01T00:00:00+00:00"
        end_ts = "2024-01-01T00:00:01+00:00"
        trace_id = "abc"
        span_id = "def"
        parent_event_id = ""
        event = "evt"
        command = "cmd"
        status = "ok"
        service = "svc"
        level = "INFO"
        workspace_id = "ws"
        agent_id = "agent"
        artifact_fingerprint = "fp"
        schema_version = "1.0"
        event_schema_version = "1.0"
        decision_source_refs = []
        duration_ms = 1
        tokens_input = 1
        tokens_output = 1
        tokens_total = 1
        context_bytes_loaded = 1
        context_budget_bytes = 1
        budget_utilization_pct = 1.0
        compression_ratio = 1.0
        retry_count = 1
        reflection_count = 1
        path_id = "A"

    attrs = OtelAttributes.from_event(DummyEvent())
    exporter.export(DummyEvent(), attrs)
    assert called["url"] == "https://fake-endpoint"
    assert b"resourceSpans" in called["data"]
    assert called["headers"]["content-type"] == "application/json"


def test_otel_attributes_to_dict_and_otel_dict():
    class DummyEvent:
        ts = "2024-01-01T00:00:00+00:00"
        end_ts = "2024-01-01T00:00:01+00:00"
        trace_id = "abc"
        span_id = "def"
        parent_event_id = ""
        event = "evt"
        command = "cmd"
        status = "ok"
        service = "svc"
        level = "INFO"
        workspace_id = "ws"
        agent_id = "agent"
        artifact_fingerprint = "fp"
        schema_version = "1.0"
        event_schema_version = "1.0"
        decision_source_refs = []
        duration_ms = 1
        tokens_input = 1
        tokens_output = 1
        tokens_total = 1
        context_bytes_loaded = 1
        context_budget_bytes = 1
        budget_utilization_pct = 1.0
        compression_ratio = 1.0
        retry_count = 1
        reflection_count = 1
        path_id = "A"

    attrs = OtelAttributes.from_event(DummyEvent())
    d = attrs.to_dict()
    od = attrs.to_otel_dict()
    assert isinstance(d, dict)
    assert isinstance(od, dict)
    assert d["trace_id"] == "abc"
    # to_otel_dict() uses dotted-key names per OTEL standard
    assert od["sdd.event"] == "evt"
