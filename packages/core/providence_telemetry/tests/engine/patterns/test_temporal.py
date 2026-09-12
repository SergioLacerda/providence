import re

from providence_telemetry.engine.patterns.temporal import TEMPORAL_PATTERNS


def test_temporal_has_five_patterns() -> None:
    assert len(TEMPORAL_PATTERNS) == 5


def test_ts001_is_iso_timestamp() -> None:
    p = TEMPORAL_PATTERNS["TS001"]
    assert p["name"] == "ISO 8601 Timestamp"
    assert "timestamp" in p["fields"]
    assert "regex" in p


def test_ts003_duration_covers_latency_fields() -> None:
    p = TEMPORAL_PATTERNS["TS003"]
    assert "latency" in p["fields"]
    assert "duration" in p["fields"]


def test_all_temporal_patterns_have_required_keys() -> None:
    for pid, pattern in TEMPORAL_PATTERNS.items():
        assert "name" in pattern, f"{pid} missing name"
        assert "fields" in pattern, f"{pid} missing fields"
        assert "compression_ratio" in pattern, f"{pid} missing compression_ratio"
        assert "frequency" in pattern, f"{pid} missing frequency"


def _match_ts001(value: str) -> bool:
    return bool(re.match(TEMPORAL_PATTERNS["TS001"]["regex"], value))


def test_ts001_matches_z_suffix() -> None:
    assert _match_ts001("2026-05-21T10:00:00Z")
    assert _match_ts001("2026-05-21T10:00:00.123Z")


def test_ts001_matches_utc_offset() -> None:
    assert _match_ts001("2026-05-21T10:00:00+00:00")


def test_ts001_matches_negative_offset() -> None:
    assert _match_ts001("2026-05-21T10:00:00-03:00")


def test_ts001_matches_positive_offset() -> None:
    assert _match_ts001("2026-05-21T05:30:00+05:30")


def test_ts001_rejects_plain_date() -> None:
    assert not _match_ts001("2026-05-21")
