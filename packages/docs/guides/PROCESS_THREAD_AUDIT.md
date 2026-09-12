# Process/Thread Audit (Phase 1-2)

Date: 2026-05-16

## Scope

Phase 1 focuses on process/subprocess standardization.
Threading was audited statically to produce a prioritized backlog.
Automated thread hotspot report is generated at `docs/guides/THREAD_AUDIT_REPORT.md`
via `uv run python tools/maintenance/thread_audit_report.py`.

## Process Findings

### P0 (fixed in this phase)

- Direct subprocess execution bypassing canonical runner:
  - `packages/interfaces/providence_cli/src/providence_cli/commands/tools.py`
  - `packages/core/providence_runtime/src/providence_runtime/skills.py` (fallback path)

### P1 (remaining)

- Tests that still patch raw `subprocess` as primary execution seam should migrate to `SafeProcessRunner` contract tests where possible.
- Optional: consolidate command-specific execution policy docs into one canonical process policy document.

## Threading Findings (Static Audit)

### P0 (fixed in phase 2)

- `metrics serve` background lifecycle was hardened:
  - stop signal via `threading.Event`
  - deterministic shutdown with `server_close()` and worker `join()`
  - restart cycle tests added

### P1

- Metrics command starts background threads for live reload:
  - `packages/interfaces/providence_cli/src/providence_cli/commands/metrics.py`
- Residual risk: explicit thread creation remains and should keep deterministic lifecycle tests as regression guard.

### P2

- In-process collectors use locks (`RLock`) with broad scope:
  - `packages/core/providence_runtime/src/providence_runtime/metrics.py`
- Risk: potential contention under high-frequency event ingestion (low risk in current workload profile).

### P2

- Tests spawn HTTP servers with background threads:
  - `packages/interfaces/providence_cli/tests/test_metrics_commands.py`
- Risk: flakiness from timing windows; improve deterministic shutdown patterns.

## Backlog for Phase 2 (Threads)

1. Add lock contention micro-benchmark for runtime collector. Status: done (`tools/maintenance/metrics_lock_benchmark.py`).
2. Introduce explicit thread ownership/lifecycle doc for CLI services that spawn background workers. Status: done (`docs/guides/THREAD_LIFECYCLE_OWNERSHIP.md`).
3. Expand resilience tests for repeated service churn under CI load. Status: done (`test_serve_soak_restart_cycles`, 30 cycles, documented in `THREAD_LIFECYCLE_OWNERSHIP.md`).
