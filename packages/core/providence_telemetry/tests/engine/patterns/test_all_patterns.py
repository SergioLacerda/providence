from providence_telemetry.engine.patterns import (
    IDENTIFIER_PATTERNS,
    MESSAGE_PATTERNS,
    METADATA_PATTERNS,
    NETWORK_PATTERNS,
    TEMPORAL_PATTERNS,
    TYPE_PATTERNS,
    get_all_patterns,
)


def test_get_all_patterns_returns_50_plus() -> None:
    patterns = get_all_patterns()
    assert len(patterns) >= 50


def test_required_ids_present() -> None:
    patterns = get_all_patterns()
    assert "TS001" in patterns
    assert "META002" in patterns
    assert "ID001" in patterns
    assert "TYPE004" in patterns


def test_all_patterns_have_name_and_fields() -> None:
    for pid, pattern in get_all_patterns().items():
        assert "name" in pattern, f"{pid} missing 'name'"
        assert "fields" in pattern, f"{pid} missing 'fields'"
        assert len(pattern["fields"]) > 0, f"{pid} has empty fields"


def test_all_patterns_have_regex_or_values() -> None:
    for pid, pattern in get_all_patterns().items():
        has_regex = "regex" in pattern
        has_values = "values" in pattern
        assert has_regex or has_values, f"{pid} has neither regex nor values"


def test_category_counts() -> None:
    assert len(TEMPORAL_PATTERNS) == 5
    assert len(NETWORK_PATTERNS) == 8
    assert len(IDENTIFIER_PATTERNS) == 10
    assert len(TYPE_PATTERNS) == 12
    assert len(MESSAGE_PATTERNS) == 8
    assert len(METADATA_PATTERNS) == 7


def test_no_duplicate_ids_across_categories() -> None:
    all_ids: list[str] = []
    for d in [
        TEMPORAL_PATTERNS,
        NETWORK_PATTERNS,
        IDENTIFIER_PATTERNS,
        TYPE_PATTERNS,
        MESSAGE_PATTERNS,
        METADATA_PATTERNS,
    ]:
        all_ids.extend(d.keys())
    assert len(all_ids) == len(set(all_ids)), "Duplicate pattern IDs across categories"


def test_compression_ratio_in_range() -> None:
    for pid, pattern in get_all_patterns().items():
        if "compression_ratio" in pattern:
            ratio = pattern["compression_ratio"]
            assert 0.0 <= ratio <= 1.0, f"{pid} compression_ratio {ratio} out of range"


def test_frequency_in_range() -> None:
    for pid, pattern in get_all_patterns().items():
        if "frequency" in pattern:
            freq = pattern["frequency"]
            assert 0.0 <= freq <= 1.0, f"{pid} frequency {freq} out of range"
