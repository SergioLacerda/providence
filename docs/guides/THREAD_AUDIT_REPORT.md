# Thread Audit Report

Static audit of `threading` hotspots in production modules.

- Findings: 3
- P0: 0
- P1: 3
- P2: 0

## Findings

| Priority | File | Line | Rule | Snippet |
|---|---|---:|---|---|
| P1 | `packages/core/providence_runtime/src/providence_runtime/metrics.py` | 138 | `rlock-usage` | `self._lock = threading.RLock()` |
| P1 | `packages/interfaces/providence_cli/src/providence_cli/commands/metrics.py` | 31 | `rlock-usage` | `self._lock = threading.RLock()` |
| P1 | `packages/interfaces/providence_cli/src/providence_cli/commands/metrics.py` | 67 | `thread-start` | `worker = threading.Thread(` |

## Priority Rules

- `P0`: daemon thread lifecycle risk or broad lock scope needing explicit shutdown checks.
- `P1`: explicit thread creation / RLock usage requiring deterministic lifecycle tests.
- `P2`: lower-risk patterns requiring documentation and periodic review.

## Regeneration

```bash
uv run python tools/maintenance/thread_audit_report.py
```
