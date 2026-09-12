from __future__ import annotations

from providence_telemetry.otel.protocol import OtelExporter


class _MinimalExporter:
    def export_event(self, attributes, *, trace_id=None, span_id=None) -> None:
        pass

    def shutdown(self) -> None:
        pass


class _MissingShutdown:
    def export_event(self, attributes, *, trace_id=None, span_id=None) -> None:
        pass


class _MissingExportEvent:
    def shutdown(self) -> None:
        pass


def test_minimal_exporter_satisfies_protocol() -> None:
    assert isinstance(_MinimalExporter(), OtelExporter)


def test_missing_shutdown_fails_protocol() -> None:
    assert not isinstance(_MissingShutdown(), OtelExporter)


def test_missing_export_event_fails_protocol() -> None:
    assert not isinstance(_MissingExportEvent(), OtelExporter)


def test_plain_object_fails_protocol() -> None:
    assert not isinstance(object(), OtelExporter)


def test_protocol_is_runtime_checkable() -> None:
    exporter = _MinimalExporter()
    result = isinstance(exporter, OtelExporter)
    assert result is True


class _InheritedImpl(OtelExporter):
    """Subclass that inherits Protocol default implementations (the pass bodies)."""


def test_inherited_export_event_default_returns_none() -> None:
    impl = _InheritedImpl()
    result = impl.export_event({"key": "val"}, trace_id="t1", span_id="s1")
    assert result is None


def test_inherited_shutdown_default_returns_none() -> None:
    impl = _InheritedImpl()
    result = impl.shutdown()
    assert result is None
