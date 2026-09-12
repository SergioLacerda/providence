# SDD Security Demos

Standalone demos and regression tools for SDD governance enforcement.
All files run independently from the repo root with `uv run python`.

---

## Enforcement Demos

Seven demos showing each enforcement mechanism in isolation.

| # | File | Mechanism | Mandate |
|---|------|-----------|---------|
| 1 | `demo_unauthorized_skill.py` | `SkillEngine` blocks unregistered skill | Registry |
| 2 | `demo_token_budget_breach.py` | `TokenBudget` circuit-breaker (WARN→BLOCK) | M005 |
| 3 | `demo_session_drift_scoring.py` | `SessionDriftScorer` PATH overload detection | Entropy |
| 4 | `demo_artifact_missing.py` | `PolicyEngine` + `SchemaValidator` preflight | Core |
| 5 | `demo_reflection_cap.py` | `RetryBudget` cuts runaway reflection loops | M005 |
| 6 | `demo_telemetry_enforcement.py` | `TelemetrySink` + `AlertDispatcher` audit trail | M007/M009 |
| 7 | `demo_handshake_failure.py` | `validate_awakening_profile` bootstrap gate | M015 |

```bash
# Run all demos at once
for demo in examples/security/demo_*.py; do
    echo "=== $demo ===" && uv run python "$demo"
done
```

---

## Drift Accuracy Battery

`drift_battery.py` — deterministic regression harness for measuring drift impact across features.

### Purpose

Run before and after implementing a feature to detect governance drift regressions.
Unlike the simulation demos, this tool measures **real accuracy** against the actual `.providence/metadata.json` artifact.

### Battery composition (100 sessions, fixed)

| Session type | Count | Fingerprint used | Expected result |
|---|---|---|---|
| `clean` | 70 | Current artifact fp | Never drift |
| `stale` | 15 | Previous run's fp | Drift only if artifact changed |
| `missing` | 10 | Empty | Always drift |
| `corrupt` | 5 | `deadbeefcafebabe` | Always drift |

### Usage

```bash
# Step 1 — before the feature: establish baseline
uv run python examples/security/drift_battery.py --label "before-auth-refactor"

# Step 2 — implement feature, recompile artifact
providence governance compile

# Step 3 — after the feature: compare
uv run python examples/security/drift_battery.py --label "after-auth-refactor"
```

### Interpreting results

| Drift rate | Artifact changed? | Meaning |
|---|---|---|
| 15% | No | Normal steady state — only `missing` + `corrupt` drift |
| 30% | Yes | Expected after `providence governance compile` — stale sessions need refresh |
| 30% | No | Regression — investigate new drift source |
| False positives > 0 | Any | Detector error — clean sessions are being flagged |
| Detection rate < 100% | Any | Missed detections — drift not being caught |

### Options

```bash
uv run python examples/security/drift_battery.py --label "my-feature" --snapshot path/to/snap.json
```

The snapshot is saved to `drift_battery_snapshot.json` by default (gitignored — local state only).

---

## Drift Benchmark (Stress / Performance)

`demo_drift_benchmark.py` — Monte Carlo stress test for throughput and scenario exploration.

> **Note:** This tool simulates sessions with configurable weights. It does not measure real drift — use `drift_battery.py` for real accuracy measurement. Use this tool for performance benchmarking or hypothetical scenario analysis.

```bash
# Default run (calibrated to real audit.txt — ~10% drift)
uv run python examples/security/demo_drift_benchmark.py

# Custom scenario
uv run python examples/security/demo_drift_benchmark.py --sessions 1000 --runs 100 --threshold 12
```

---

## Notes

- All demos require `.providence/metadata.json` (run `providence governance compile` if missing).
- Demos 2, 3, 5, and 6 are self-contained and do not read governance files.
- `drift_battery_snapshot.json` is local state — do not commit it.
