"""
Collectors for SDD Telemetry.
Provides base classes and implementations for metrics collection.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any


class BaseCollector(ABC):
    """Base class for all telemetry collectors"""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def collect(self) -> dict[str, Any]:
        """Collect metrics and return as a dictionary"""
        pass


class MetricsRegistry:
    """Registry to manage multiple collectors"""

    def __init__(self) -> None:
        self._collectors: dict[str, BaseCollector] = {}

    def register(self, collector: BaseCollector) -> None:
        """Register a new collector"""
        self._collectors[collector.name] = collector

    def collect_all(self) -> dict[str, Any]:
        """Run all registered collectors"""
        results: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {},
        }
        for name, collector in self._collectors.items():
            results["metrics"][name] = collector.collect()
        return results
