"""Collector for binary serialization size metrics (JSON vs msgpack)."""

from dataclasses import dataclass
from typing import Any

from ..collectors import BaseCollector


@dataclass
class BinaryMetrics:
    """Stores raw size measurements for a single binary encoding comparison."""

    json_size: int = 0
    msgpack_size: int = 0
    string_pool_size: int = 0
    # Informational multiplier: msgpack deserialization speed relative to JSON (typically 3.5×).
    # Included in to_dict() output for reporting purposes only — does not affect compression.
    speedup_factor: float = 3.5

    @property
    def compression_ratio(self) -> float:
        """Fraction of bytes saved by msgpack relative to JSON (0.0 if no data)."""
        if self.json_size == 0:
            return 0.0
        return (self.json_size - self.msgpack_size) / self.json_size

    def to_dict(self) -> dict[str, Any]:
        """Return all metrics as a plain dict for collector output."""
        return {
            "json_size": self.json_size,
            "msgpack_size": self.msgpack_size,
            "string_pool_size": self.string_pool_size,
            "compression_ratio": self.compression_ratio,
            "speedup_factor": self.speedup_factor,
        }


class BinaryCollector(BaseCollector):
    """Collector that tracks JSON vs msgpack payload sizes per telemetry event."""

    def __init__(
        self, name: str = "binary_metrics", speedup_factor: float = 3.5
    ) -> None:
        """Initialize the collector.

        Args:
            name: Collector name used as key in MetricsRegistry.collect_all().
            speedup_factor: Msgpack deserialization speedup relative to JSON. Informational only.
        """
        super().__init__(name)
        self._metrics = BinaryMetrics(speedup_factor=speedup_factor)

    def update(self, json_size: int, msgpack_size: int, string_pool_size: int) -> None:
        """Record the latest size measurements for the current event."""
        self._metrics.json_size = json_size
        self._metrics.msgpack_size = msgpack_size
        self._metrics.string_pool_size = string_pool_size

    def collect(self) -> dict[str, Any]:
        """Return the current binary metrics snapshot."""
        return self._metrics.to_dict()
