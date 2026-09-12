"""Package-wide constants shared across providence_telemetry modules."""

from __future__ import annotations

SEVERITY_NUMBER: dict[str, int] = {
    "TRACE": 1,
    "DEBUG": 5,
    "INFO": 9,
    "WARN": 13,
    "WARNING": 13,
    "ERROR": 17,
    "FATAL": 21,
    "CRITICAL": 21,
}

DEFAULT_SEVERITY = "INFO"
DEFAULT_SERVICE_NAME = "providence-runtime"
DEFAULT_SERVICE_VERSION = "unknown"

SDD_NAMESPACE = "sdd."

DEFAULT_CACHE_SIZE = 1000

PATTERN_COVERAGE_TARGET = 0.90
