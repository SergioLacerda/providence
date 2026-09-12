"""Snapshot contract checks for `providence_telemetry` hot-path benchmarks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.perf]

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


def _load_pyproject() -> dict:
    return tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))


def _telemetry_perf_config() -> dict:
    data = _load_pyproject()
    perf = data["tool"]["sdd"]["performance"]["telemetry"]
    assert isinstance(perf, dict), "Missing [tool.sdd.performance.telemetry] section"
    return perf


def test_telemetry_snapshot_exists_and_has_expected_sections() -> None:
    snapshot = Path("tests/perf/providence_telemetry_benchmark_results.json")
    assert snapshot.exists(), "Missing telemetry benchmark snapshot"
    data = json.loads(snapshot.read_text(encoding="utf-8"))

    assert "registry" in data
    assert "deduplication" in data
    assert "timestamp_helper" in data
    assert "targets" in data


def test_telemetry_snapshot_respects_declared_thresholds() -> None:
    perf = _telemetry_perf_config()
    snapshot = Path("tests/perf/providence_telemetry_benchmark_results.json")
    data = json.loads(snapshot.read_text(encoding="utf-8"))

    assert (
        data["registry"]["timestamp_match"]["p95_us"] <= perf["registry_lookup_p95_us"]
    )
    assert data["registry"]["uuid_match"]["p95_us"] <= perf["registry_lookup_p95_us"]
    assert (
        data["deduplication"]["cold_engine"]["p95_us"]
        <= perf["deduplicate_cold_p95_us"]
    )
    assert (
        data["deduplication"]["warm_cache_hit"]["p95_us"]
        <= perf["deduplicate_warm_p95_us"]
    )
    assert (
        data["timestamp_helper"]["cached_timestamp"]["p95_us"]
        <= perf["cached_timestamp_p95_us"]
    )
