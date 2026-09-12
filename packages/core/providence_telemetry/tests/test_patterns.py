"""Tests for pattern categories."""

from providence_telemetry.engine.patterns import (
    IDENTIFIER_PATTERNS,
    MESSAGE_PATTERNS,
    METADATA_PATTERNS,
    NETWORK_PATTERNS,
    TEMPORAL_PATTERNS,
    TYPE_PATTERNS,
    get_all_patterns,
)
from providence_telemetry.engine.registry import PatternRegistry


class TestPatternCategories:
    def test_total_pattern_count(self) -> None:
        assert len(get_all_patterns()) >= 50

    def test_category_sizes(self) -> None:
        assert len(TEMPORAL_PATTERNS) == 5
        assert len(NETWORK_PATTERNS) == 8
        assert len(IDENTIFIER_PATTERNS) == 10
        assert len(TYPE_PATTERNS) == 12
        assert len(MESSAGE_PATTERNS) == 8
        assert len(METADATA_PATTERNS) == 7

    def test_temporal_patterns_present(self) -> None:
        assert "TS001" in TEMPORAL_PATTERNS
        assert TEMPORAL_PATTERNS["TS001"]["name"] == "ISO 8601 Timestamp"
        assert "TS002" in TEMPORAL_PATTERNS
        assert "TS003" in TEMPORAL_PATTERNS

    def test_network_patterns_present(self) -> None:
        assert "NET001" in NETWORK_PATTERNS
        assert "NET004" in NETWORK_PATTERNS

    def test_identifier_patterns_present(self) -> None:
        assert "ID001" in IDENTIFIER_PATTERNS
        assert "ID010" in IDENTIFIER_PATTERNS

    def test_type_patterns_present(self) -> None:
        assert "TYPE001" in TYPE_PATTERNS
        assert "TYPE004" in TYPE_PATTERNS
        assert "TYPE008" in TYPE_PATTERNS

    def test_message_patterns_present(self) -> None:
        assert "MSG001" in MESSAGE_PATTERNS
        assert "MSG005" in MESSAGE_PATTERNS

    def test_metadata_patterns_present(self) -> None:
        assert "META001" in METADATA_PATTERNS
        assert "META002" in METADATA_PATTERNS


class TestPatternMatching:
    def test_iso_timestamp(self) -> None:
        r = PatternRegistry()
        assert r.find_pattern("timestamp", "2026-05-21T10:00:00Z") == "TS001"

    def test_unix_timestamp(self) -> None:
        r = PatternRegistry()
        assert r.find_pattern("unix_time", "1716278400") is not None

    def test_duration_ms(self) -> None:
        r = PatternRegistry()
        assert r.find_pattern("latency", "150ms") == "TS003"

    def test_ipv4_address(self) -> None:
        r = PatternRegistry()
        assert r.find_pattern("ip", "192.168.0.1") == "NET001"

    def test_http_url(self) -> None:
        r = PatternRegistry()
        assert r.find_pattern("url", "https://example.com/api") == "NET004"

    def test_uuid(self) -> None:
        r = PatternRegistry()
        assert (
            r.find_pattern("trace_id", "550e8400-e29b-41d4-a716-446655440000")
            == "ID001"
        )

    def test_log_level(self) -> None:
        r = PatternRegistry()
        assert r.find_pattern("log_level", "ERROR") == "TYPE005"

    def test_http_method(self) -> None:
        r = PatternRegistry()
        assert r.find_pattern("method", "GET") == "TYPE006"

    def test_environment(self) -> None:
        r = PatternRegistry()
        assert r.find_pattern("env", "production") == "TYPE008"

    def test_semantic_version(self) -> None:
        r = PatternRegistry()
        assert r.find_pattern("version", "1.2.3") == "META001"

    def test_service_name(self) -> None:
        r = PatternRegistry()
        assert r.find_pattern("service", "sdd-api") == "META002"

    def test_no_match_returns_none(self) -> None:
        r = PatternRegistry()
        assert r.find_pattern("unknown_xyz", "anything") is None
