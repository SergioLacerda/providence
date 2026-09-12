from providence_telemetry.otel.noop import NoopExporter
from providence_telemetry.otel.protocol import OtelExporter


def test_noop_export_event_does_not_raise() -> None:
    exporter = NoopExporter()
    exporter.export_event({"service.name": "test"})


def test_noop_export_event_with_trace_span_ids() -> None:
    exporter = NoopExporter()
    exporter.export_event({}, trace_id="t-1", span_id="s-1")


def test_noop_shutdown_does_not_raise() -> None:
    exporter = NoopExporter()
    exporter.shutdown()


def test_noop_satisfies_otel_exporter_protocol() -> None:
    assert isinstance(NoopExporter(), OtelExporter)


def test_noop_export_returns_none() -> None:
    exporter = NoopExporter()
    result = exporter.export_event({"x": 1})
    assert result is None
