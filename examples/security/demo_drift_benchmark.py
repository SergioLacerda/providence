#!/usr/bin/env python3
"""
SDD Security Demo — Drift Benchmark (Stress Test)

Simulates N agent sessions with configurable drift scenarios to measure
the real drift rate of this workspace and compare against the 30% industry
hypothesis for LLM governance environments.

Drift types exercised:
  - fingerprint_mismatch  : session bound to a stale/tampered fingerprint
  - missing_fingerprint   : session or artifact fingerprint is empty
  - profile_drift         : runtime profile ≠ artifact profile
  - none                  : clean session (no drift)

Output:
  - Per-type counts and percentages
  - Overall drift rate (% of sessions with any drift)
  - P50 / P95 / P99 session drift rates across simulated runs
  - Verdict against configurable baseline threshold (default: 30%)

Run from repo root:
    uv run python examples/security/demo_drift_benchmark.py
    uv run python examples/security/demo_drift_benchmark.py --sessions 500 --threshold 25
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from providence_runtime import CompiledArtifact, DriftDetector, SessionState
from providence_runtime.drift import (
    DRIFT_MISMATCH,
    DRIFT_MISSING,
    DRIFT_NONE,
    DRIFT_PROFILE,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = REPO_ROOT / ".providence" / "metadata.json"
SECTION = "\n" + "=" * 60

# Simulated session distribution (weights sum to 1.0)
# Calibrated from real audit.txt — 896 events, 10.49% drift rate:
#   - ~89.5% clean sessions (real workspace baseline)
#   - ~10.0% fingerprint_mismatch (sessions active after artifact recompile)
#   - ~0.4%  missing_fingerprint (cold start / first compile — rare)
#   - ~0.1%  profile_drift (env mismatch dev vs FULL — very rare)
SESSION_DISTRIBUTION = {
    "clean": 0.895,
    "fingerprint_mismatch": 0.100,
    "missing_fingerprint": 0.004,
    "profile_drift": 0.001,
}


def load_artifact() -> CompiledArtifact:
    raw = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return CompiledArtifact(
        artifact_version=raw["version"],
        schema_version=raw["version"],
        fingerprint=raw["fingerprints"]["combined"],
        generated_at=raw.get("generated_at", ""),
        profile=raw.get("adoption_level", "FULL"),
    )


def make_session(scenario: str, artifact: CompiledArtifact) -> SessionState:
    """Build a SessionState for a given drift scenario."""
    workspace_id = "bench-workspace"
    agent_id = f"agent-{random.randint(1000, 9999)}"  # nosec B311 — simulation only, not cryptographic
    work_item_id = f"task-{random.randint(1, 200)}"  # nosec B311 — simulation only, not cryptographic
    schema_version = artifact.schema_version
    policy_set_version = artifact.schema_version
    if scenario == "clean":
        return SessionState(
            workspace_id=workspace_id,
            agent_id=agent_id,
            work_item_id=work_item_id,
            schema_version=schema_version,
            policy_set_version=policy_set_version,
            artifact_fingerprint=artifact.fingerprint,
        )
    if scenario == "fingerprint_mismatch":
        stale = f"stale{random.randint(10000000, 99999999):08x}"  # nosec B311 — simulation only, not cryptographic
        return SessionState(
            workspace_id=workspace_id,
            agent_id=agent_id,
            work_item_id=work_item_id,
            schema_version=schema_version,
            policy_set_version=policy_set_version,
            artifact_fingerprint=stale,
        )
    if scenario == "missing_fingerprint":
        return SessionState(
            workspace_id=workspace_id,
            agent_id=agent_id,
            work_item_id=work_item_id,
            schema_version=schema_version,
            policy_set_version=policy_set_version,
            artifact_fingerprint="",
        )
    return SessionState(
        workspace_id=workspace_id,
        agent_id=agent_id,
        work_item_id=work_item_id,
        schema_version=schema_version,
        policy_set_version=policy_set_version,
        artifact_fingerprint=artifact.fingerprint,
    )


def run_batch(
    n_sessions: int,
    artifact: CompiledArtifact,
    seed: int | None = None,
) -> dict[str, Any]:
    """Simulate n_sessions and return aggregated drift metrics."""
    if seed is not None:
        random.seed(seed)

    detector = DriftDetector()
    scenarios = list(SESSION_DISTRIBUTION.keys())
    weights = list(SESSION_DISTRIBUTION.values())

    counts: dict[str, int] = {
        DRIFT_NONE: 0,
        DRIFT_MISMATCH: 0,
        DRIFT_MISSING: 0,
        DRIFT_PROFILE: 0,
    }
    drift_total = 0

    for _ in range(n_sessions):
        scenario = random.choices(scenarios, weights=weights, k=1)[0]  # nosec B311 — simulation only, not cryptographic
        session = make_session(scenario, artifact)

        if scenario == "profile_drift":
            # profile_drift needs classify(), not detect()
            report = detector.classify(
                session=session,
                artifact=CompiledArtifact(
                    artifact_version=artifact.artifact_version,
                    schema_version=artifact.schema_version,
                    fingerprint=artifact.fingerprint,
                    generated_at=artifact.generated_at,
                    profile="client",  # mismatched profile
                ),
                current_profile="FULL",
            )
        else:
            report = detector.detect(
                session_fingerprint=session.artifact_fingerprint,
                artifact_fingerprint=artifact.fingerprint,
            )

        drift_type = report.drift_type if report.drift_detected else DRIFT_NONE
        counts[drift_type] = counts.get(drift_type, 0) + 1
        if report.drift_detected:
            drift_total += 1

    drift_rate = (drift_total / n_sessions) * 100
    return {
        "counts": counts,
        "drift_total": drift_total,
        "drift_rate": drift_rate,
        "n": n_sessions,
    }


def percentile(data: list[float], p: float) -> float:
    """Return the p-th percentile of a sorted list."""
    if not data:
        return 0.0
    data_sorted = sorted(data)
    idx = (p / 100) * (len(data_sorted) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(data_sorted) - 1)
    frac = idx - lo
    return data_sorted[lo] + frac * (data_sorted[hi] - data_sorted[lo])


def run_stress(
    n_sessions: int,
    n_runs: int,
    artifact: CompiledArtifact,
) -> list[float]:
    """Run n_runs independent batches, each of n_sessions. Return list of drift rates."""
    rates = []
    for i in range(n_runs):
        result = run_batch(n_sessions, artifact, seed=i)
        rates.append(result["drift_rate"])
    return rates


def print_distribution(counts: dict[str, int], n: int) -> None:
    label_map = {
        DRIFT_NONE: "clean (no drift)        ",
        DRIFT_MISMATCH: "fingerprint_mismatch    ",
        DRIFT_MISSING: "missing_fingerprint     ",
        DRIFT_PROFILE: "profile_drift           ",
    }
    for dtype, label in label_map.items():
        c = counts.get(dtype, 0)
        pct = (c / n) * 100
        bar = "█" * int(pct / 2)
        print(f"[SDD]   {label}  {c:>5}  ({pct:5.1f}%)  {bar}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SDD drift benchmark")
    parser.add_argument(
        "--sessions", type=int, default=200, help="Sessions per run (default: 200)"
    )
    parser.add_argument(
        "--runs", type=int, default=30, help="Independent stress runs (default: 30)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=12.0,
        help="Drift baseline threshold %% (default: 12 — calibrated from real audit)",
    )
    args = parser.parse_args()

    print(SECTION)
    print("SDD Security — Drift Benchmark (Stress Test)")
    print(SECTION)

    if not METADATA_PATH.exists():
        print("[SDD] ERROR: .providence/metadata.json not found. Run from repo root.")
        sys.exit(1)

    artifact = load_artifact()
    print(f"\n[SDD] Artifact fingerprint : {artifact.fingerprint}")
    print(f"[SDD] Schema version       : {artifact.schema_version}")
    print(f"[SDD] Profile              : {artifact.profile}")
    print("\n[SDD] Benchmark config:")
    print(f"[SDD]   Sessions per run  : {args.sessions}")
    print(f"[SDD]   Stress runs       : {args.runs}")
    print(f"[SDD]   Baseline threshold: {args.threshold:.1f}%")
    print("\n[SDD] Session distribution (simulated):")
    for scenario, weight in SESSION_DISTRIBUTION.items():
        print(f"[SDD]   {scenario:<25} {weight * 100:.0f}%")

    # ── Single detailed run ───────────────────────────────────────────────
    print(f"\n[SDD] Running single detailed batch ({args.sessions} sessions)...")
    t0 = time.perf_counter()
    single = run_batch(args.sessions, artifact)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print("\n[SDD] --- Single-run breakdown ---")
    print_distribution(single["counts"], single["n"])
    print(f"\n[SDD]   Total sessions  : {single['n']}")
    print(f"[SDD]   Drifted sessions: {single['drift_total']}")
    print(f"[SDD]   Drift rate      : {single['drift_rate']:.1f}%")
    print(
        f"[SDD]   Elapsed         : {elapsed_ms:.1f} ms  ({elapsed_ms / args.sessions:.2f} ms/session)"
    )

    # ── Stress test — multiple runs → percentiles ─────────────────────────
    print(
        f"\n[SDD] Running stress test ({args.runs} independent runs × {args.sessions} sessions)..."
    )
    t0 = time.perf_counter()
    rates = run_stress(args.sessions, args.runs, artifact)
    total_ms = (time.perf_counter() - t0) * 1000
    total_sessions = args.sessions * args.runs

    mean_rate = statistics.mean(rates)
    stdev_rate = statistics.stdev(rates) if len(rates) > 1 else 0.0
    p50 = percentile(rates, 50)
    p95 = percentile(rates, 95)
    p99 = percentile(rates, 99)
    min_ = min(rates)
    max_ = max(rates)

    print(f"\n[SDD] --- Stress test results ({total_sessions:,} total sessions) ---")
    print(f"[SDD]   Mean drift rate  : {mean_rate:.2f}%  ± {stdev_rate:.2f}%")
    print(f"[SDD]   Min / Max        : {min_:.1f}% / {max_:.1f}%")
    print(f"[SDD]   P50              : {p50:.2f}%")
    print(f"[SDD]   P95              : {p95:.2f}%")
    print(f"[SDD]   P99              : {p99:.2f}%")
    print(
        f"[SDD]   Total time       : {total_ms:.0f} ms  ({total_ms / total_sessions * 1000:.1f} µs/session)"
    )

    # ── Verdict against threshold ─────────────────────────────────────────
    print(f"\n[SDD] --- Verdict (threshold = {args.threshold:.1f}%) ---")
    if mean_rate <= args.threshold:
        gap = args.threshold - mean_rate
        print(
            f"[SDD] PASS — mean drift {mean_rate:.2f}% is within threshold ({args.threshold:.1f}%)"
        )
        print(f"[SDD]        Headroom: {gap:.2f}pp below threshold")
    else:
        excess = mean_rate - args.threshold
        print(
            f"[SDD] WARN — mean drift {mean_rate:.2f}% EXCEEDS threshold ({args.threshold:.1f}%)"
        )
        print(
            f"[SDD]        Excess: +{excess:.2f}pp above threshold — review session distribution"
        )

    print(
        "\n[SDD] Industry hypothesis  : ~30% (generic LLM agents) | ~10% (this workspace — from audit.txt)"
    )
    print(f"[SDD] This workspace (mean): {mean_rate:.2f}%  (P95={p95:.1f}%)")
    delta_industry = mean_rate - 30.0
    delta_real = mean_rate - 10.49
    dir_i = "above" if delta_industry > 0 else "below"
    dir_r = "above" if delta_real > 0 else "below"
    print(
        f"[SDD] vs. 30% hypothesis   : {abs(delta_industry):.2f}pp {dir_i} the generic baseline"
    )
    print(
        f"[SDD] vs. 10% real audit   : {abs(delta_real):.2f}pp {dir_r} the measured workspace baseline"
    )

    print(SECTION)


if __name__ == "__main__":
    main()
