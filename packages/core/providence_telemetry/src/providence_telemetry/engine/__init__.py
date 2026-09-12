"""Telemetry engine: deduplication, LRU cache, pattern registry, and pattern sets."""

from providence_telemetry.types import CompressionMetrics

from .cache import LRUCache
from .deduplicator import DeduplicationEngine
from .patterns import get_all_patterns
from .registry import PatternRegistry

__all__ = [
    "CompressionMetrics",
    "DeduplicationEngine",
    "LRUCache",
    "PatternRegistry",
    "get_all_patterns",
]
