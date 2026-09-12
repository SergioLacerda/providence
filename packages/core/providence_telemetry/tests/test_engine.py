"""Tests for DeduplicationEngine and PatternRegistry."""

from typing import Any

from providence_telemetry.engine.cache import LRUCache
from providence_telemetry.engine.deduplicator import DeduplicationEngine
from providence_telemetry.engine.registry import PatternRegistry
from providence_telemetry.types import CompressionMetrics


def _registry() -> PatternRegistry:
    return PatternRegistry()


def _engine() -> DeduplicationEngine:
    return DeduplicationEngine()


class TestPatternRegistry:
    def test_timestamp_pattern_detection(self) -> None:
        registry = _registry()
        assert registry.find_pattern("timestamp", "2026-04-21T14:30:00Z") == "TS001"

    def test_service_pattern_detection(self) -> None:
        registry = _registry()
        assert registry.find_pattern("service", "sdd-api") is not None

    def test_version_pattern_detection(self) -> None:
        registry = _registry()
        assert registry.find_pattern("version", "3.1.0") is not None

    def test_status_code_pattern_detection(self) -> None:
        registry = _registry()
        expected = registry.find_pattern("status", 200)
        assert expected is not None
        for status in [200, 201, 400, 404, 500]:
            assert registry.find_pattern("status", status) == expected
        assert registry.find_pattern("status", 999) is None

    def test_uuid_pattern_detection(self) -> None:
        registry = _registry()
        assert (
            registry.find_pattern("trace_id", "550e8400-e29b-41d4-a716-446655440000")
            is not None
        )

    def test_non_matching_field(self) -> None:
        assert _registry().find_pattern("unknown_field", "random_value") is None

    def test_pattern_lookup_by_id(self) -> None:
        pattern = _registry().get_pattern("TS001")
        assert pattern is not None
        assert pattern["name"] == "ISO 8601 Timestamp"
        assert "regex" in pattern


class TestDeduplicationEngine:
    def test_simple_timestamp_deduplication(self) -> None:
        engine = _engine()
        event = {"timestamp": "2026-04-21T14:30:00Z", "message": "Test"}
        compressed = engine.deduplicate(event)
        expected = f"${engine._registry.find_pattern('timestamp', event['timestamp'])}"
        assert compressed["timestamp"] == expected
        assert compressed["message"] == "Test"

    def test_multiple_field_deduplication(self) -> None:
        engine = _engine()
        event = {
            "timestamp": "2026-04-21T14:30:00Z",
            "service": "sdd-api",
            "version": "3.1.0",
            "status": 200,
        }
        compressed = engine.deduplicate(event)
        assert compressed["timestamp"].startswith("$")
        # "sdd-api" (7 chars) → token "$META002" (8 chars): longer, keep original
        assert compressed["service"] == "sdd-api"
        # "3.1.0" (5 chars) → token "$META001" (8 chars): longer, keep original
        assert compressed["version"] == "3.1.0"
        # status 200 (int, str="200" 3 chars) → token "$TYPE004" (8 chars): longer, keep original
        assert compressed["status"] == 200

    def test_uuid_deduplication(self) -> None:
        engine = _engine()
        uuid_val = "550e8400-e29b-41d4-a716-446655440000"
        compressed = engine.deduplicate({"trace_id": uuid_val})
        assert (
            compressed["trace_id"].startswith("$") or "#UUID:" in compressed["trace_id"]
        )

    def test_mixed_pattern_and_no_pattern_fields(self) -> None:
        engine = _engine()
        event = {
            "timestamp": "2026-04-21T14:30:00Z",
            "user_name": "alice",
            "status": 200,
            "description": "Done",
        }
        compressed = engine.deduplicate(event)
        assert compressed["timestamp"].startswith("$")
        assert compressed["user_name"] == "alice"
        assert compressed["description"] == "Done"

    def test_nested_structure_deduplication(self) -> None:
        engine = _engine()
        event: dict[str, Any] = {
            "timestamp": "2026-04-21T14:30:00Z",
            "metadata": {"service": "sdd-api", "version": "3.1.0"},
        }
        compressed = engine.deduplicate(event)
        assert compressed["timestamp"].startswith("$")
        assert compressed["metadata"]["service"] == event["metadata"]["service"]

    def test_list_deduplication(self) -> None:
        engine = _engine()
        event = {"timestamps": ["2026-04-21T14:30:00Z", "2026-04-21T14:31:00Z"]}
        compressed = engine.deduplicate(event)
        assert all(
            isinstance(ts, str) and (ts.startswith("$") or ts.startswith("#TS:"))
            for ts in compressed["timestamps"]
        )


class TestCaching:
    def test_cache_hit_on_duplicate_event(self) -> None:
        engine = _engine()
        event = {"timestamp": "2026-04-21T14:30:00Z", "service": "sdd-api"}
        compressed1 = engine.deduplicate(event)
        assert engine.get_metrics().cache_misses == 1
        assert engine.get_metrics().cache_hits == 0
        compressed2 = engine.deduplicate(event)
        assert engine.get_metrics().cache_hits == 1
        assert compressed1 == compressed2

    def test_cache_size_limit(self) -> None:
        engine = DeduplicationEngine(cache=LRUCache(max_size=3))
        events = [{"timestamp": f"2026-04-21T14:{i:02d}:00Z"} for i in range(5)]
        for event in events:
            engine.deduplicate(event)
        assert len(engine._cache) <= 3

    def test_cache_clear(self) -> None:
        engine = _engine()
        engine.deduplicate({"timestamp": "2026-04-21T14:30:00Z"})
        assert len(engine._cache) > 0
        engine.clear_cache()
        assert len(engine._cache) == 0

    def test_cache_disabled_when_max_size_is_zero(self) -> None:
        engine = DeduplicationEngine(cache=LRUCache(max_size=0))
        compressed = engine.deduplicate({"timestamp": "2026-04-21T14:30:00Z"})
        assert isinstance(compressed, dict)
        assert len(engine._cache) == 0


class TestCompressionMetrics:
    def test_compression_ratio_calculation(self) -> None:
        metrics = CompressionMetrics(256, 64, 4, 5, 1)
        assert metrics.compression_ratio == 0.75

    def test_cache_hit_ratio_calculation(self) -> None:
        metrics = CompressionMetrics(100, 25, 3, 8, 2)
        assert metrics.cache_hit_ratio == 0.8

    def test_zero_division_protection(self) -> None:
        metrics = CompressionMetrics(0, 0, 0, 0, 0)
        assert metrics.compression_ratio == 0.0
        assert metrics.cache_hit_ratio == 0.0


class TestValueEncoding:
    def test_timestamp_encoding(self) -> None:
        engine = _engine()
        encoded = engine._encode_value("2026-04-21T14:30:00Z")
        assert isinstance(encoded, str)

    def test_uuid_encoding(self) -> None:
        engine = _engine()
        uuid_val = "550e8400-e29b-41d4-a716-446655440000"
        encoded = engine._encode_value(uuid_val)
        assert isinstance(encoded, str)
        assert "UUID" in encoded or uuid_val in encoded

    def test_numeric_values_preserved(self) -> None:
        engine = _engine()
        assert engine._encode_value(42) == 42
        assert engine._encode_value(3.14) == 3.14
        assert engine._encode_value(0) == 0

    def test_boolean_values_preserved(self) -> None:
        engine = _engine()
        assert engine._encode_value(True) is True
        assert engine._encode_value(False) is False

    def test_none_value_preserved(self) -> None:
        assert _engine()._encode_value(None) is None

    def test_unhandled_object_value_passthrough(self) -> None:
        marker = object()
        assert _engine()._encode_value(marker) is marker


class TestTimestampEncoding:
    def test_invalid_timestamp_returns_original(self) -> None:
        assert DeduplicationEngine._encode_timestamp("not-a-date") == "not-a-date"

    def test_empty_string_returns_original(self) -> None:
        assert DeduplicationEngine._encode_timestamp("") == ""

    def test_valid_timestamp_returns_compact_ref(self) -> None:
        assert DeduplicationEngine._encode_timestamp("2026-04-21T14:30:00Z").startswith(
            "#TS:"
        )


class TestEdgeCases:
    def test_empty_event(self) -> None:
        assert _engine().deduplicate({}) == {}

    def test_very_large_event(self) -> None:
        engine = _engine()
        event = {f"field_{i}": f"2026-04-21T14:{i % 60:02d}:00Z" for i in range(1000)}
        compressed = engine.deduplicate(event)
        assert all(
            isinstance(v, str) and v.startswith("#TS:") for v in compressed.values()
        )

    def test_special_characters_in_values(self) -> None:
        engine = _engine()
        event = {"description": "Special chars: @#$%^&*()"}
        compressed = engine.deduplicate(event)
        assert "@" in compressed["description"]
