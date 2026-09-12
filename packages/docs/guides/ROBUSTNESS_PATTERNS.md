# Robustness Patterns Guide

This guide describes the runtime robustness mechanisms currently implemented for
governed skills.

It focuses on the execution behavior in
`packages/core/providence_runtime/src/providence_runtime/_skill_executor.py`, not on broader
platform reliability topics.

## Scope

The current robustness model covers:

- bounded command timeouts
- retry classification for transient failures
- retry hooks and timeout hooks for artifact capture
- pipeline-level escalation on stage failure, timeout, or freeze
- partial externalization of orchestration gates

This is a runtime snapshot of what exists today.

## Timeout Model

Each skill inherits a timeout budget from `skill.budget_policy.timeout_seconds`.

Current behavior:

- commands execute through `SafeProcessRunner.run(..., timeout=timeout_seconds)`
- process timeouts are normalized to `exit_code=124`
- standalone timed-out executions return `policy_result="timeout"`
- `Handler.timeout_hook()` can persist timeout-specific artifacts

Default timeout handling records:

- a `timeout_event` artifact
- a `FailureLedgerEntry` with `symptom="timeout"` when learning is available

This keeps timeouts visible both in command results and in the supervised
learning ledger.

## Retry Model

Retries are opt-in per failed command attempt, bounded by
`skill.budget_policy.max_retries`.

The executor treats a failure as retryable when either:

- `Handler.can_retry(...)` returns `True`
- or the default retry classifier matches the failure

Current default retry classifier accepts:

- `exit_code == 124`
- errors containing `temporary`
- errors containing `temporarily`
- errors containing `timeout` or `timed out`
- errors containing `rate limit`
- errors containing `try again`

Current backoff implementation is intentionally short:

- `wait_seconds = min(0.01 * (2 ** attempt), 0.05)`

That means the runtime has exponential backoff semantics, but with test-friendly
sub-second waits rather than long operational sleeps.

## Retry And Timeout Hooks

The base `Handler` contract includes:

- `can_retry(...)`
- `retry_hook(...)`
- `timeout_hook(...)`

The default hooks produce audit-friendly artifacts:

- `retry_hook(...)` records a `retry_event` artifact and appends a ledger entry
  with `symptom="retry"`
- `timeout_hook(...)` records a `timeout_event` artifact and appends a ledger
  entry with `symptom="timeout"`

This allows individual handlers to override retryability or artifact shape
without duplicating executor mechanics.

## Pipeline Escalation Patterns

`sdd-pipeline` reuses the same execution engine and adds stage-aware escalation.

Current pipeline stop conditions:

- low diagnosis confidence after `sdd-diagnose`
- `freeze_mode_state.enabled` after `sdd-converge`
- stage timeout (`exit_code == 124`)
- any non-zero stage exit

Current pipeline robustness artifacts:

- `pipeline_gate_decision`
- `pipeline_escalation`
- `pipeline_timeout`
- `pipeline_state`

Pipeline stage timeouts are escalated, not downgraded to standalone timeout
success semantics. The result reason is normalized as
`stage_timeout:<stage-name>`.

## Gate Externalization Status

Gate evaluation now supports declarative rule expressions loaded from per-skill
YAML files.

Implemented today:

- `sdd-pipeline` reads `config.pipeline.decision_gates`
- `sdd-correct` loads `.providence/skills/sdd-correct/gate-rules.yaml`
- correction gate rules use a structured `when` DSL with deterministic operators
- invalid rule schemas fail closed before correction execution

## Failure Semantics

The executor normalizes failures into predictable outputs:

- command-level failure metadata in `command_results`
- `exit_code=124` for timeout
- `policy_result="timeout"` for isolated command timeout
- `policy_result="escalated"` for pipeline timeout or governed stop conditions
- `policy_result="denied"` for invalid correction gate rule schemas

This makes automation simpler because timeout and escalation are not inferred
from free-form stderr alone.

## Operational Guidance

- Keep timeout and retry policy in `budget_policy`, not ad-hoc command wrappers.
- Prefer handler overrides for skill-specific retry behavior.
- Treat pipeline timeout as an orchestration failure, not a transient success.
- Keep gate facts narrow, but prefer declarative YAML expressions over new
  hardcoded condition switches.

## References

- `packages/core/providence_runtime/src/providence_runtime/_skill_executor.py`
- `packages/core/providence_runtime/tests/test_skill_executor.py`
- `docs/guides/PIPELINE_ORCHESTRATION.md`
- `docs/guides/LEARNING_INTEGRATION.md`
- `docs/spec/canonical/core/economy/efficiency-policy.md`
