# Process Runner Exceptions

Date: 2026-05-16

Direct `subprocess` usage is blocked by default. The canonical execution path is
`providence_core.utils.process.SafeProcessRunner`.

## Allowed Exceptions

- `packages/core/providence_core/src/providence_core/utils/process.py`
  - Reason: canonical governed process implementation (`subprocess` wrapper layer).

## Enforced Guardrails

- `packages/*`: no direct subprocess outside canonical runner.
- Migrated critical tools must stay subprocess-free:
  - `tools/testing/run-all-tests.py`
  - `tools/health/health_check.py`
  - `tools/governance/compliance.py`
  - `tools/maintenance/lint_all.py`
  - `tools/testing/diagnostics.py`
  - `tools/testing/update-golden-snapshots.py`

Validated by `tests/unit/test_process_runner_guardrails.py`.
