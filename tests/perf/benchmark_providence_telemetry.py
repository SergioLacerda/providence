"""Standalone benchmark for `providence_telemetry` hot paths.

Measures `PatternRegistry.find_pattern()` and `DeduplicationEngine.deduplicate()`
using deterministic fixtures so the results can be versioned as a lightweight
performance snapshot.

Usage:
    python tests/perf/benchmark_providence_telemetry.py
    python tests/perf/benchmark_providence_telemetry.py --output tests/perf/providence_telemetry_benchmark_results.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _src in (
    _REPO_ROOT,
    _REPO_ROOT / "packages/core/providence_telemetry/src",
):
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from providence_telemetry.engine.deduplicator import DeduplicationEngine  # noqa: E402
from providence_telemetry.engine.registry import PatternRegistry  # noqa: E402

DEFAULT_OUTPUT = Path("tests/perf/providence_telemetry_benchmark_results.json")
REGISTRY_ITERATIONS = 20_000
DEDUP_ITERATIONS = 5_000
TIMESTAMP_ITERATIONS = 20_000


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = round((len(ordered) - 1) * quantile)
    return ordered[index]


def _run_many(fn: Any, iterations: int) -> list[float]:
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        fn()
        elapsed_ns = time.perf_counter_ns() - start
        samples.append(elapsed_ns / 1_000)
    return samples


def _summarize(samples_us: list[float]) -> dict[str, float]:
    return {
        "min_us": round(min(samples_us), 3),
        "p50_us": round(statistics.median(samples_us), 3),
        "p95_us": round(_percentile(samples_us, 0.95), 3),
        "max_us": round(max(samples_us), 3),
        "mean_us": round(statistics.fmean(samples_us), 3),
    }


def _registry_benchmark() -> dict[str, Any]:
    registry = PatternRegistry()

    def timestamp_case() -> Any:
        return registry.find_pattern("timestamp", "2026-05-21T10:00:00Z")

    def uuid_case() -> Any:
        return registry.find_pattern("trace_id", "550E8400-E29B-41D4-A716-446655440000")

    def miss_case() -> Any:
        return registry.find_pattern("custom_field", "plain-text-value")

    return {
        "iterations": REGISTRY_ITERATIONS,
        "timestamp_match": _summarize(_run_many(timestamp_case, REGISTRY_ITERATIONS)),
        "uuid_match": _summarize(_run_many(uuid_case, REGISTRY_ITERATIONS)),
        "miss": _summarize(_run_many(miss_case, REGISTRY_ITERATIONS)),
    }


def _dedup_benchmark() -> dict[str, Any]:
    event = {
        "timestamp": "2026-05-21T10:00:00Z",
        "trace_id": "550E8400-E29B-41D4-A716-446655440000",
        "status": 200,
        "content_type": "application/json",
        "meta": {"region": "sa-east-1", "attempt": 3},
        "tags": ["governance", "telemetry", "cache"],
    }

    warm_engine = DeduplicationEngine()
    warm_engine.deduplicate(event)

    def warm_case() -> Any:
        return warm_engine.deduplicate(event)

    def cold_case() -> Any:
        return DeduplicationEngine().deduplicate(event)

    return {
        "iterations": DEDUP_ITERATIONS,
        "warm_cache_hit": _summarize(_run_many(warm_case, DEDUP_ITERATIONS)),
        "cold_engine": _summarize(_run_many(cold_case, DEDUP_ITERATIONS)),
    }


def _timestamp_helper_benchmark() -> dict[str, Any]:
    helper = DeduplicationEngine._encode_timestamp
    helper("2026-05-21T10:00:00Z")

    def cached_case() -> Any:
        return helper("2026-05-21T10:00:00Z")

    def miss_case() -> Any:
        return helper("2026-05-21T10:00:01Z")

    return {
        "iterations": TIMESTAMP_ITERATIONS,
        "cached_timestamp": _summarize(_run_many(cached_case, TIMESTAMP_ITERATIONS)),
        "new_timestamp": _summarize(_run_many(miss_case, TIMESTAMP_ITERATIONS)),
    }


def build_results() -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "targets": {
            "registry_lookup_p95_us": 10.0,
            "deduplicate_cold_p95_us": 100.0,
            "deduplicate_warm_p95_us": 12.0,
            "cached_timestamp_p95_us": 1.0,
        },
        "registry": _registry_benchmark(),
        "deduplication": _dedup_benchmark(),
        "timestamp_helper": _timestamp_helper_benchmark(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark providence_telemetry hot paths"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSON path",
    )
    args = parser.parse_args(argv)

    results = build_results()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
