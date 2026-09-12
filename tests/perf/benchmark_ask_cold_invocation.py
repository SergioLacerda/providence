"""Standalone benchmark for `providence ask` cold-invocation wall time (T-U1).

Splits one `providence ask` CLI call's wall time into two measurable pieces:
- a baseline `import providence_cli` cost (process/interpreter startup), and
- the full `providence ask <query>` call time, from which the baseline is
  subtracted to estimate governance-snapshot assembly cost.

Every invocation is a fresh subprocess (`python -m providence_cli ask ...`),
matching how `providence ask` is actually used — see
`.analysis/refined/20260730-sdd-ask-tu1-cold-invocation-benchmark/design.md`
D2. Reports percentiles rather than a pass/fail budget: full-process timing
is noisy (OS scheduling, disk cache state), so results are directional, not
a strict regression gate — same posture as the other `tests/perf/*.py`
scripts in this directory, none of which assert a budget.

Usage:
    python tests/perf/benchmark_ask_cold_invocation.py
    python tests/perf/benchmark_ask_cold_invocation.py --output tests/perf/benchmark_ask_cold_invocation_results.json
    python tests/perf/benchmark_ask_cold_invocation.py --iterations 10
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = Path("tests/perf/benchmark_ask_cold_invocation_results.json")
DEFAULT_ITERATIONS = 20

# Representative query set (design.md D2 / analysis.md U2): a routing-decision
# cache hit (same query repeated), a cold/novel query (routing-decision miss),
# and a --dossier call (a heavier, separately-cached path).
_QUERIES: list[dict[str, Any]] = [
    {
        "label": "repeated_query",
        "args": ["ask", "benchmark repeated query for cold invocation timing"],
    },
    {
        "label": "novel_query",
        "args": ["ask", "benchmark novel query {i} for cold invocation timing"],
        "vary_per_iteration": True,
    },
    {
        "label": "dossier_query",
        "args": [
            "ask",
            "benchmark dossier query for cold invocation timing",
            "--dossier",
        ],
    },
]


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = round((len(ordered) - 1) * quantile)
    return ordered[index]


def _summarize(samples_ms: list[float]) -> dict[str, float]:
    return {
        "min_ms": round(min(samples_ms), 3),
        "p50_ms": round(statistics.median(samples_ms), 3),
        "p95_ms": round(_percentile(samples_ms, 0.95), 3),
        "max_ms": round(max(samples_ms), 3),
        "mean_ms": round(statistics.fmean(samples_ms), 3),
    }


def _time_subprocess(argv: list[str]) -> float:
    """Run `argv` as a subprocess and return elapsed wall time in ms."""
    start = time.perf_counter()
    subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return (time.perf_counter() - start) * 1000


def _benchmark_import_baseline(iterations: int) -> dict[str, float]:
    """Time `python -c "import providence_cli"` — the process/interpreter startup floor."""
    samples = [
        _time_subprocess([sys.executable, "-c", "import providence_cli"])
        for _ in range(iterations)
    ]
    return _summarize(samples)


def _benchmark_query(query_spec: dict[str, Any], iterations: int) -> dict[str, Any]:
    samples: list[float] = []
    for i in range(iterations):
        args = [
            arg.format(i=i) if query_spec.get("vary_per_iteration") else arg
            for arg in query_spec["args"]
        ]
        samples.append(
            _time_subprocess([sys.executable, "-m", "providence_cli", *args])
        )
    return {
        "label": query_spec["label"],
        "full_call_ms": _summarize(samples),
    }


def build_results(iterations: int = DEFAULT_ITERATIONS) -> dict[str, Any]:
    baseline = _benchmark_import_baseline(iterations)
    queries = [_benchmark_query(spec, iterations) for spec in _QUERIES]

    for entry in queries:
        # Directional estimate only (D2): subtracts the import-baseline p50
        # from each query's own percentiles. Can be negative/noisy on a
        # loaded machine — report as-is rather than clamping, so the raw
        # signal is visible.
        full = entry["full_call_ms"]
        entry["estimated_assembly_ms"] = {
            key: round(full[key] - baseline["p50_ms"], 3) for key in full
        }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "iterations": iterations,
        "baseline_import_ms": baseline,
        "queries": queries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark providence ask cold-invocation wall time"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSON path",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_ITERATIONS,
        help="Subprocess invocations per measurement (default: 20)",
    )
    args = parser.parse_args(argv)

    results = build_results(args.iterations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
