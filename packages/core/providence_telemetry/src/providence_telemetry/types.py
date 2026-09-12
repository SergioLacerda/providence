"""Core data types shared across the providence_telemetry package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict


@dataclass
class CompressionMetrics:
    """Counters accumulated by the deduplication engine during event processing."""

    original_size: int
    compressed_size: int
    pattern_matches: int
    cache_hits: int
    cache_misses: int

    @property
    def compression_ratio(self) -> float:
        """Fraction of bytes saved by compression (0.0 when no data processed)."""
        if self.original_size == 0:
            return 0.0
        return (self.original_size - self.compressed_size) / self.original_size

    @property
    def cache_hit_ratio(self) -> float:
        """Fraction of lookups served from cache (0.0 when no lookups recorded)."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total


class _PatternDefBase(TypedDict):
    name: str
    fields: list[str]


class PatternDef(_PatternDefBase, total=False):
    """Full pattern definition extending the required base with optional regex/values."""

    regex: str
    values: list[Any]
    compression_ratio: float
    frequency: float
