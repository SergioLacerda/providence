"""SDD Telemetry — metrics, deduplication and OTel integration."""

__version__ = "2.0.0"

from .collectors import BaseCollector, MetricsRegistry
from .collectors.binary import BinaryCollector, BinaryMetrics
from .collectors.confidence import ConfidenceCollector
from .engine import CompressionMetrics, DeduplicationEngine, LRUCache, PatternRegistry
from .engine.patterns import get_all_patterns
from .otel import NoopExporter, OtelExporter, to_otel_attributes

__all__ = [
    "BaseCollector",
    "MetricsRegistry",
    "BinaryCollector",
    "BinaryMetrics",
    "ConfidenceCollector",
    "CompressionMetrics",
    "DeduplicationEngine",
    "LRUCache",
    "PatternRegistry",
    "get_all_patterns",
    "OtelExporter",
    "NoopExporter",
    "to_otel_attributes",
]
