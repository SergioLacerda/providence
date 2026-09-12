from __future__ import annotations

from providence_telemetry.collectors import BaseCollector, MetricsRegistry


class _DummyCollector(BaseCollector):
    def __init__(self, name: str, value: int) -> None:
        super().__init__(name)
        self._value = value

    def collect(self) -> dict[str, int]:
        return {"value": self._value}


def test_metrics_registry_register_and_collect_all() -> None:
    registry = MetricsRegistry()
    registry.register(_DummyCollector("alpha", 1))
    registry.register(_DummyCollector("beta", 2))
    payload = registry.collect_all()
    assert "timestamp" in payload
    assert payload["metrics"]["alpha"] == {"value": 1}
    assert payload["metrics"]["beta"] == {"value": 2}
