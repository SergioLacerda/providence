"""In-process cache-hit vs. cache-miss timing for `build_governed_ask_snapshot`
(T-U1, design.md D3  `.analysis/refined/20260730-sdd-ask-tu1-cold-invocation-benchmark/`).

A regression guard, not a report artifact: confirms the snapshot cache
(T-A1-A3) still delivers a real, measurable speedup on a hit, without
depending on the real repo's compiled-governance state (which may not exist
in every environment this runs in). `_load_compiled_governance` is replaced
with a small deterministic delay standing in for "real I/O work"  the
timing signal being tested is whether the hit path skips that call entirely
(already proven by call-count assertions in `test_ask_governance_snapshot_
cache.py`), not the real duration of a live compiled-governance load.

Report-only beyond the sanity assertion (no hard millisecond budget yet)
design.md D3's own risk note defers a hard budget assertion (T-BM4) until a
real baseline exists from `tests/perf/benchmark_ask_cold_invocation.py`.
"""

from __future__ import annotations

import statistics
import time
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.perf]

_ITERATIONS = 30
_SIMULATED_LOAD_DELAY_SECONDS = 0.01


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = round((len(ordered) - 1) * quantile)
    return ordered[index]


def _time_snapshot_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    warm_cache: bool,
    iterations: int,
) -> list[float]:
    from providence_cli.commands import _ask_backend as _backend
    from providence_cli.commands._ask_backend import _pipeline_snapshot as _pipeline
    from providence_cli.services import ask_context_routing as ask_context_routing_mod

    def _slow_load_compiled_governance(root: Path) -> tuple:
        time.sleep(_SIMULATED_LOAD_DELAY_SECONDS)
        return ("compiled", "fp1", 16, True, False, "", "canonical")

    class _FakeReport:
        status = "ok"
        diagnostic = ""
        matches: list[dict] = []

    monkeypatch.setattr(
        _backend, "_load_compiled_governance", _slow_load_compiled_governance
    )
    monkeypatch.setattr(_backend, "_guard_handshake", lambda root: None)
    monkeypatch.setattr(_backend, "_runtime_drift_check", lambda root, fp: False)
    monkeypatch.setattr(_backend, "_root_seed_drift_check", lambda root: False)
    monkeypatch.setattr(
        "providence_cli.services.governance_docs_handbook_lookup.lookup_runtime_handbook",
        lambda root, *, task_type, operation_phase: _FakeReport(),
    )

    if warm_cache:
        ask_context_routing_mod.write_runtime_cache_and_routing_decision(
            tmp_path,
            {"compiled_fingerprint_used": "fp1"},
            "prior query",
            None,
            "fp1",
            {"organize_used": False},
            {
                "context_source": "compiled",
                "fingerprint": "fp1",
                "mandates_count": 16,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "canonical",
            },
        )

    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        _pipeline.build_governed_ask_snapshot(
            query="perf timing query",
            skill=None,
            organize_used=False,
            workspace_root=tmp_path,
            require_handshake=True,
        )
        samples.append((time.perf_counter() - start) * 1000)
    return samples


def test_snapshot_cache_hit_is_faster_than_miss(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A cache hit must be measurably faster than a miss.

    Cold start (miss) pays `_SIMULATED_LOAD_DELAY_SECONDS` every call; a warm
    cache (hit) skips `_load_compiled_governance` entirely per design.md D-A,
    so it should be close to instant by comparison.
    """
    miss_samples = _time_snapshot_calls(
        monkeypatch, tmp_path / "miss", warm_cache=False, iterations=_ITERATIONS
    )
    hit_samples = _time_snapshot_calls(
        monkeypatch, tmp_path / "hit", warm_cache=True, iterations=_ITERATIONS
    )

    miss_p50 = statistics.median(miss_samples)
    hit_p50 = statistics.median(hit_samples)
    miss_p95 = _percentile(miss_samples, 0.95)
    hit_p95 = _percentile(hit_samples, 0.95)

    print(
        f"\nmiss: p50={miss_p50:.3f}ms p95={miss_p95:.3f}ms | "
        f"hit: p50={hit_p50:.3f}ms p95={hit_p95:.3f}ms | "
        f"speedup={miss_p50 / hit_p50:.1f}x"
    )

    assert hit_p50 < miss_p50, (
        f"cache hit (p50={hit_p50:.3f}ms) must be faster than a miss "
        f"(p50={miss_p50:.3f}ms)  the snapshot cache may not be skipping "
        f"_load_compiled_governance on a hit anymore"
    )
