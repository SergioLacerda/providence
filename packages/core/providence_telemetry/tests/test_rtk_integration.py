"""RTK (Runtime Telemetry Kit) integration tests."""

from providence_telemetry import (
    CompressionMetrics,
    DeduplicationEngine,
    PatternRegistry,
    get_all_patterns,
)


class TestRTKIntegration:
    def test_rtk_available(self) -> None:
        assert DeduplicationEngine is not None
        assert PatternRegistry is not None

    def test_pattern_registry_loads(self) -> None:
        registry = PatternRegistry()
        assert len(registry.patterns) >= 50
        assert "TS001" in registry.patterns
        assert "META002" in registry.patterns

    def test_deduplicate_event_basic(self) -> None:
        engine = DeduplicationEngine()
        event = {
            "timestamp": "2026-04-21T14:30:00Z",
            "service": "sdd-api",
            "status": 200,
        }
        compressed = engine.deduplicate(event)
        assert "$" in str(compressed)

    def test_compression_metrics(self) -> None:
        engine = DeduplicationEngine()
        event = {
            "timestamp": "2026-04-21T14:30:00Z",
            "service": "sdd-api",
            "version": "3.1.0",
            "status": 200,
            "response_time": "150ms",
        }
        engine.deduplicate(event)
        metrics = engine.get_metrics()
        assert isinstance(metrics, CompressionMetrics)
        assert metrics.original_size > 0
        assert metrics.compressed_size > 0

    def test_get_all_patterns_available(self) -> None:
        patterns = get_all_patterns()
        assert len(patterns) > 40


class TestRTKPatternMatching:
    def test_timestamp_pattern(self) -> None:
        engine = DeduplicationEngine()
        compressed = engine.deduplicate({"timestamp": "2026-04-21T14:30:00Z"})
        assert compressed is not None

    def test_http_status_pattern(self) -> None:
        engine = DeduplicationEngine()
        for status in [200, 201, 204, 400, 401, 403, 404, 500]:
            compressed = engine.deduplicate({"status": status})
            assert compressed is not None

    def test_multiple_events_compression(self) -> None:
        engine = DeduplicationEngine()
        events = [
            {"timestamp": "2026-04-21T14:30:00Z", "service": "sdd-api", "status": 200},
            {"timestamp": "2026-04-21T14:30:01Z", "service": "sdd-api", "status": 200},
            {
                "timestamp": "2026-04-21T14:30:02Z",
                "service": "sdd-compiler",
                "status": 201,
            },
        ]
        total_original = sum(len(str(e)) for e in events)
        compressed_events = [engine.deduplicate(e) for e in events]
        total_compressed = sum(len(str(e)) for e in compressed_events)
        assert total_original >= total_compressed
