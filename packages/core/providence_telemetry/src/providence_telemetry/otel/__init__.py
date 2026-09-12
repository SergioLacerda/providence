"""OTel integration: attribute converter, exporter protocol, and no-op default."""

from .attributes import to_otel_attributes
from .noop import NoopExporter
from .protocol import OtelExporter

__all__ = [
    "OtelExporter",
    "NoopExporter",
    "to_otel_attributes",
]
