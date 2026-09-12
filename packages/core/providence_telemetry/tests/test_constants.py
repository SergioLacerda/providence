from providence_telemetry.constants import (
    DEFAULT_CACHE_SIZE,
    DEFAULT_SERVICE_NAME,
    DEFAULT_SERVICE_VERSION,
    DEFAULT_SEVERITY,
    PATTERN_COVERAGE_TARGET,
    SDD_NAMESPACE,
    SEVERITY_NUMBER,
)


def test_severity_number_has_all_levels() -> None:
    expected = {
        "TRACE",
        "DEBUG",
        "INFO",
        "WARN",
        "WARNING",
        "ERROR",
        "FATAL",
        "CRITICAL",
    }
    assert expected == set(SEVERITY_NUMBER.keys())


def test_severity_number_values_are_ints() -> None:
    for key, value in SEVERITY_NUMBER.items():
        assert isinstance(value, int), f"{key} should be int"


def test_severity_number_ordering() -> None:
    assert SEVERITY_NUMBER["TRACE"] < SEVERITY_NUMBER["DEBUG"]
    assert SEVERITY_NUMBER["DEBUG"] < SEVERITY_NUMBER["INFO"]
    assert SEVERITY_NUMBER["INFO"] < SEVERITY_NUMBER["WARN"]
    assert SEVERITY_NUMBER["WARN"] < SEVERITY_NUMBER["ERROR"]
    assert SEVERITY_NUMBER["ERROR"] < SEVERITY_NUMBER["FATAL"]
    assert SEVERITY_NUMBER["WARN"] == SEVERITY_NUMBER["WARNING"]
    assert SEVERITY_NUMBER["FATAL"] == SEVERITY_NUMBER["CRITICAL"]


def test_defaults_are_strings() -> None:
    assert isinstance(DEFAULT_SEVERITY, str)
    assert isinstance(DEFAULT_SERVICE_NAME, str)
    assert isinstance(DEFAULT_SERVICE_VERSION, str)


def test_sdd_namespace_ends_with_dot() -> None:
    assert SDD_NAMESPACE.endswith(".")


def test_default_cache_size_is_positive_int() -> None:
    assert isinstance(DEFAULT_CACHE_SIZE, int)
    assert DEFAULT_CACHE_SIZE > 0


def test_pattern_coverage_target_is_fraction() -> None:
    assert 0.0 < PATTERN_COVERAGE_TARGET <= 1.0
