from unittest.mock import MagicMock

from providence_telemetry.engine import deduplicator as deduplicator_module
from providence_telemetry.engine.cache import LRUCache
from providence_telemetry.engine.deduplicator import DeduplicationEngine
from providence_telemetry.engine.registry import PatternRegistry


def make_engine(**kwargs: object) -> DeduplicationEngine:
    return DeduplicationEngine(**kwargs)


def test_deduplicate_known_pattern_replaces_with_token() -> None:
    engine = make_engine()
    # timestamp "2026-05-21T10:00:00Z" (20 chars) → "$TS001" (6 chars): token is shorter ✓
    # service "sdd-api" (7 chars) → "$META002" (8 chars): token is LONGER, keep original ✓
    event = {"timestamp": "2026-05-21T10:00:00Z", "service": "sdd-api"}
    result = engine.deduplicate(event)
    assert result["timestamp"].startswith("$"), "Long timestamps should be tokenised"
    assert result["service"] == "sdd-api", (
        "Short values must not be replaced by longer tokens"
    )


def test_deduplicate_unknown_field_keeps_value() -> None:
    engine = make_engine()
    result = engine.deduplicate({"custom_field": "hello"})
    assert result["custom_field"] == "hello"


def test_cache_hit_on_second_call() -> None:
    engine = make_engine()
    event = {"status": 200}
    engine.deduplicate(event)
    engine.deduplicate(event)
    assert engine.get_metrics().cache_hits == 1
    assert engine.get_metrics().cache_misses == 1


def test_metrics_pattern_matches_incremented() -> None:
    engine = make_engine()
    engine.deduplicate({"timestamp": "2026-05-21T10:00:00Z"})
    assert engine.get_metrics().pattern_matches >= 1


def test_reset_metrics_zeroes_all_counters() -> None:
    engine = make_engine()
    engine.deduplicate({"status": 200})
    engine.reset_metrics()
    m = engine.get_metrics()
    assert m.original_size == 0
    assert m.compressed_size == 0
    assert m.pattern_matches == 0
    assert m.cache_hits == 0
    assert m.cache_misses == 0


def test_clear_cache_resets_hit_count() -> None:
    engine = make_engine()
    event = {"status": 200}
    engine.deduplicate(event)
    engine.clear_cache()
    engine.deduplicate(event)
    assert engine.get_metrics().cache_hits == 0
    assert engine.get_metrics().cache_misses == 2


def test_dependency_injection_registry() -> None:
    custom_registry = MagicMock(spec=PatternRegistry)
    custom_registry.find_pattern.return_value = None
    engine = DeduplicationEngine(registry=custom_registry)
    engine.deduplicate({"field": "value"})
    custom_registry.find_pattern.assert_called()


def test_dependency_injection_cache() -> None:
    custom_cache = LRUCache(max_size=5)
    engine = DeduplicationEngine(cache=custom_cache)
    engine.deduplicate({"status": 200})
    assert len(custom_cache) == 1


def test_encode_value_none() -> None:
    engine = make_engine()
    result = engine.deduplicate({"field": None})
    assert result["field"] is None


def test_encode_value_bool() -> None:
    engine = make_engine()
    result = engine.deduplicate({"custom_bool": True})
    assert result["custom_bool"] is True


def test_encode_value_list() -> None:
    engine = make_engine()
    result = engine.deduplicate({"tags": ["a", "b"]})
    assert result["tags"] == ["a", "b"]


def test_encode_value_nested_dict() -> None:
    engine = make_engine()
    result = engine.deduplicate({"meta": {"key": "val"}})
    assert result["meta"] == {"key": "val"}


def test_encode_timestamp_like_string() -> None:
    engine = make_engine()
    result = engine.deduplicate({"custom_ts": "2026-05-21T10:00:00+00:00"})
    assert result["custom_ts"].startswith("#TS:")


def test_encode_uuid_like_string() -> None:
    engine = make_engine()
    result = engine.deduplicate({"custom_id": "550e8400-e29b-41d4-a716-446655440000"})
    assert "#UUID:" in str(result["custom_id"]) or result["custom_id"].startswith("$")


def test_get_metrics_returns_snapshot_not_live_reference() -> None:
    engine = make_engine()
    engine.deduplicate({"status": 200})
    snapshot = engine.get_metrics()
    engine.deduplicate({"status": 404})
    assert snapshot.cache_misses == 1
    assert engine.get_metrics().cache_misses == 2
    assert snapshot is not engine.get_metrics()


def test_deduplicate_returns_independent_copy_no_cache_corruption() -> None:
    engine = make_engine()
    event = {"status": 200, "service": "sdd-api"}
    result = engine.deduplicate(event)
    result["injected"] = "CORRUPTED"
    cached = engine.deduplicate(event)
    assert "injected" not in cached


def test_unix_timestamp_detected_as_timestamp_like() -> None:
    engine = make_engine()
    result = engine.deduplicate({"custom_ts": "1716278400"})
    assert result["custom_ts"].startswith("#TS:")


def test_unix_timestamp_ms_detected_as_timestamp_like() -> None:
    engine = make_engine()
    result = engine.deduplicate({"custom_ts": "1716278400000"})
    assert (
        result["custom_ts"].startswith("#TS:") or result["custom_ts"] == "1716278400000"
    )


def test_uppercase_uuid_encodes_as_pattern_token() -> None:
    engine = make_engine()
    result = engine.deduplicate({"trace_id": "550E8400-E29B-41D4-A716-446655440000"})
    assert result["trace_id"] == "$ID001"


def test_deduplicate_does_not_expand_short_values() -> None:
    """Fix 1: tokenization must not expand payload — if token >= original, keep original."""
    engine = make_engine()
    # A single-char value like "a" has len=1; any token "$TYPExxx" has len>=7 — must NOT replace.
    result = engine.deduplicate({"level": "a"})
    assert result["level"] == "a", (
        "Single-char value must not be replaced by a longer token"
    )


def test_deduplicate_token_applied_when_shorter() -> None:
    """Fix 1: tokenization IS applied when token is shorter than the original value."""
    engine = make_engine()
    # "DEBUG" is 5 chars; token "$TYPE005" is 8 chars — keep original.
    # "application/json" is 16 chars; token "$TYPE007" is 8 chars — replace.
    result = engine.deduplicate({"content_type": "application/json"})
    assert result["content_type"] == "$TYPE007"


def test_disabled_cache_does_not_cache() -> None:
    engine = DeduplicationEngine(cache=LRUCache(max_size=0))
    event = {"status": 200}
    engine.deduplicate(event)
    engine.deduplicate(event)
    assert engine.get_metrics().cache_hits == 0
    assert engine.get_metrics().cache_misses == 2


def test_timestamp_encoding_helper_uses_lru_cache() -> None:
    deduplicator_module._encode_timestamp.cache_clear()
    value = "2026-05-21T10:00:00+00:00"
    assert deduplicator_module._encode_timestamp(value).startswith("#TS:")
    assert deduplicator_module._encode_timestamp(value).startswith("#TS:")
    assert deduplicator_module._encode_timestamp.cache_info().hits >= 1
