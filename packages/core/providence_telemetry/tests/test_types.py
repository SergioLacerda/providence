from providence_telemetry.types import CompressionMetrics, PatternDef


class TestCompressionMetrics:
    def test_compression_ratio_zero_original(self) -> None:
        m = CompressionMetrics(0, 0, 0, 0, 0)
        assert m.compression_ratio == 0.0

    def test_compression_ratio_positive(self) -> None:
        m = CompressionMetrics(
            original_size=100,
            compressed_size=60,
            pattern_matches=5,
            cache_hits=0,
            cache_misses=1,
        )
        assert m.compression_ratio == 0.40

    def test_compression_ratio_expansion(self) -> None:
        m = CompressionMetrics(
            original_size=100,
            compressed_size=120,
            pattern_matches=0,
            cache_hits=0,
            cache_misses=1,
        )
        assert m.compression_ratio == -0.20

    def test_cache_hit_ratio_zero_total(self) -> None:
        m = CompressionMetrics(0, 0, 0, 0, 0)
        assert m.cache_hit_ratio == 0.0

    def test_cache_hit_ratio_all_hits(self) -> None:
        m = CompressionMetrics(0, 0, 0, cache_hits=10, cache_misses=0)
        assert m.cache_hit_ratio == 1.0

    def test_cache_hit_ratio_mixed(self) -> None:
        m = CompressionMetrics(0, 0, 0, cache_hits=3, cache_misses=1)
        assert m.cache_hit_ratio == 0.75


class TestPatternDef:
    def test_pattern_def_is_typeddict(self) -> None:
        p: PatternDef = {
            "name": "Test Pattern",
            "regex": r"^\d+$",
            "fields": ["id"],
            "compression_ratio": 0.10,
            "frequency": 0.50,
        }
        assert p["name"] == "Test Pattern"
        assert p["fields"] == ["id"]

    def test_pattern_def_values_field(self) -> None:
        p: PatternDef = {
            "name": "Enum Pattern",
            "values": ["a", "b"],
            "fields": ["status"],
        }
        assert p["values"] == ["a", "b"]

    def test_pattern_def_total_false_allows_partial(self) -> None:
        p: PatternDef = {"name": "Minimal"}
        assert p["name"] == "Minimal"
