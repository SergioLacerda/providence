from providence_telemetry.collectors.binary import BinaryCollector, BinaryMetrics


def test_default_speedup_factor() -> None:
    collector = BinaryCollector()
    result = collector.collect()
    assert result["speedup_factor"] == 3.5


def test_custom_speedup_factor() -> None:
    collector = BinaryCollector(speedup_factor=4.2)
    result = collector.collect()
    assert result["speedup_factor"] == 4.2


def test_update_and_collect() -> None:
    collector = BinaryCollector()
    collector.update(json_size=100, msgpack_size=60, string_pool_size=10)
    result = collector.collect()
    assert result["json_size"] == 100
    assert result["msgpack_size"] == 60
    assert result["compression_ratio"] == 0.40


def test_compression_ratio_zero_json_size() -> None:
    metrics = BinaryMetrics()
    assert metrics.compression_ratio == 0.0


def test_compression_ratio_expansion() -> None:
    metrics = BinaryMetrics(json_size=100, msgpack_size=120)
    assert metrics.compression_ratio == -0.20


def test_to_dict_has_all_keys() -> None:
    metrics = BinaryMetrics(json_size=50, msgpack_size=30, string_pool_size=5)
    d = metrics.to_dict()
    assert set(d.keys()) == {
        "json_size",
        "msgpack_size",
        "string_pool_size",
        "compression_ratio",
        "speedup_factor",
    }


def test_custom_name() -> None:
    collector = BinaryCollector(name="my_binary")
    assert collector.name == "my_binary"


def test_metrics_attribute_is_private() -> None:
    collector = BinaryCollector()
    assert not hasattr(collector, "metrics")
    assert hasattr(collector, "_metrics")
