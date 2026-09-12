# CrewAI Demo — Spec Drift Detection

Shows SDD detecting a tampered governance fingerprint before a CrewAI crew executes.

## Run

```bash
# From repo root
uv run --extra examplescrewai python examples/crewai/demo_spec_drift.py
```

## What happens

1. A CrewAI crew is initialized with one agent and one task
2. The governance fingerprint in `.providence/metadata.json` is tampered in a temp copy (simulates drift)
3. SDD `governance validate` detects the mismatch → `DRIFT_DETECTED`
4. The crew is never kicked off — demo exits 0

## Expected output

```
[SDD] Validating governance contract...
[SDD] DRIFT_DETECTED: fingerprint mismatch
  expected : 1329516f
  found    : deadbeef
[SDD] Crew execution prevented. Governance enforced.
```
