import re

from providence_telemetry.engine.registry import PatternRegistry


def test_registry_loads_50_plus_patterns() -> None:
    registry = PatternRegistry()
    assert len(registry.patterns) >= 50


def test_required_pattern_ids_present() -> None:
    registry = PatternRegistry()
    assert "TS001" in registry.patterns
    assert "META002" in registry.patterns
    assert "ID001" in registry.patterns


def test_find_pattern_iso_timestamp() -> None:
    registry = PatternRegistry()
    result = registry.find_pattern("timestamp", "2026-05-21T10:00:00Z")
    assert result == "TS001"


def test_find_pattern_http_status_code() -> None:
    registry = PatternRegistry()
    result = registry.find_pattern("status", 200)
    assert result is not None


def test_find_pattern_log_level() -> None:
    registry = PatternRegistry()
    result = registry.find_pattern("log_level", "INFO")
    assert result == "TYPE005"


def test_find_pattern_unknown_field_returns_none() -> None:
    registry = PatternRegistry()
    result = registry.find_pattern("nonexistent_field_xyz", "some_value")
    assert result is None


def test_find_pattern_unmatched_value_returns_none() -> None:
    registry = PatternRegistry()
    result = registry.find_pattern("timestamp", "not_a_timestamp")
    assert result is None


def test_get_pattern_returns_definition() -> None:
    registry = PatternRegistry()
    pattern = registry.get_pattern("TS001")
    assert pattern is not None
    assert pattern["name"] == "ISO 8601 Timestamp"


def test_get_pattern_unknown_returns_none() -> None:
    registry = PatternRegistry()
    assert registry.get_pattern("UNKNOWN999") is None


def test_field_index_built_correctly() -> None:
    registry = PatternRegistry()
    assert "timestamp" in registry._field_index
    assert "TS001" in registry._field_index["timestamp"]


def test_patterns_property_is_read_only() -> None:
    registry = PatternRegistry()
    import pytest

    with pytest.raises(TypeError):
        registry.patterns["INJECTED"] = {"name": "hack", "fields": ["x"]}  # type: ignore[index]


def test_patterns_property_read_operations_work() -> None:
    registry = PatternRegistry()
    proxy = registry.patterns
    assert "TS001" in proxy
    assert proxy["TS001"]["name"] == "ISO 8601 Timestamp"
    assert len(proxy) >= 50


def test_find_pattern_uppercase_uuid_matches_id001() -> None:
    registry = PatternRegistry()
    assert (
        registry.find_pattern("trace_id", "550E8400-E29B-41D4-A716-446655440000")
        == "ID001"
    )


def test_find_pattern_lowercase_uuid_matches_id001() -> None:
    registry = PatternRegistry()
    assert (
        registry.find_pattern("trace_id", "550e8400-e29b-41d4-a716-446655440000")
        == "ID001"
    )


def test_regex_patterns_are_compiled_once_at_registry_init() -> None:
    registry = PatternRegistry()
    compiled = registry._compiled_regexes["TS001"]
    assert isinstance(compiled, re.Pattern)
    assert compiled.flags & re.IGNORECASE
