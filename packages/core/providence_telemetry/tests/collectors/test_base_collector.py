import pytest

from providence_telemetry.collectors import BaseCollector, MetricsRegistry


class _ConcreteCollector(BaseCollector):
    def collect(self):
        return {"value": 42}


def test_base_collector_requires_collect_implementation() -> None:
    with pytest.raises(TypeError):
        BaseCollector("test")  # type: ignore[abstract]


def test_concrete_collector_has_name() -> None:
    c = _ConcreteCollector("my_collector")
    assert c.name == "my_collector"
    assert not hasattr(c, "timestamp")


def test_metrics_registry_register_and_collect() -> None:
    registry = MetricsRegistry()
    registry.register(_ConcreteCollector("c1"))
    results = registry.collect_all()
    assert "c1" in results["metrics"]
    assert results["metrics"]["c1"] == {"value": 42}


def test_metrics_registry_collect_all_has_timestamp() -> None:
    registry = MetricsRegistry()
    registry.register(_ConcreteCollector("c1"))
    results = registry.collect_all()
    assert "timestamp" in results


def test_metrics_registry_multiple_collectors() -> None:
    registry = MetricsRegistry()
    registry.register(_ConcreteCollector("c1"))
    registry.register(_ConcreteCollector("c2"))
    results = registry.collect_all()
    assert "c1" in results["metrics"]
    assert "c2" in results["metrics"]


def test_metrics_registry_overwrites_same_name() -> None:
    registry = MetricsRegistry()
    registry.register(_ConcreteCollector("dup"))
    registry.register(_ConcreteCollector("dup"))
    results = registry.collect_all()
    assert len(results["metrics"]) == 1
