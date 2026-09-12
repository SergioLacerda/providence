from providence_telemetry.types import CompressionMetrics


def test_compression_ratio_zero_original() -> None:
    m = CompressionMetrics(0, 0, 0, 0, 0)
    assert m.compression_ratio == 0.0


def test_compression_ratio_50_percent() -> None:
    m = CompressionMetrics(200, 100, 0, 0, 1)
    assert m.compression_ratio == 0.5


def test_compression_ratio_full() -> None:
    m = CompressionMetrics(100, 0, 0, 0, 1)
    assert m.compression_ratio == 1.0


def test_compression_ratio_expansion() -> None:
    m = CompressionMetrics(100, 150, 0, 0, 1)
    assert m.compression_ratio == -0.5


def test_cache_hit_ratio_no_lookups() -> None:
    m = CompressionMetrics(0, 0, 0, 0, 0)
    assert m.cache_hit_ratio == 0.0


def test_cache_hit_ratio_all_hits() -> None:
    m = CompressionMetrics(0, 0, 0, 10, 0)
    assert m.cache_hit_ratio == 1.0


def test_cache_hit_ratio_partial() -> None:
    m = CompressionMetrics(0, 0, 0, 1, 3)
    assert m.cache_hit_ratio == 0.25
