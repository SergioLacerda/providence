# Pipeline Orchestration Guide

This guide describes how the governed runtime executes `sdd-pipeline` as a
Python-native composition of sub-skills.

## Scope

The current orchestration contract applies to:

- `sdd-pipeline`
- `sdd-ask`
- `sdd-diagnose`
- `sdd-correct`
- `sdd-converge`

The implementation lives primarily in
`packages/core/providence_runtime/src/providence_runtime/_skill_executor.py`.

## Execution Model

`sdd-pipeline` does not execute a single CLI fallback command when composition
is available. Instead:

1. `PipelineHandler.pre_run()` validates pipeline config and requests
   composition.
2. `SkillExecutor` creates a `ContextCarrier` from the incoming context.
3. Each stage executes in order, receiving a snapshot of the accumulated
   context.
4. Stage outputs are merged back into the shared carrier.
5. Runtime gates decide whether the next stage should run, skip, or escalate.

This keeps orchestration inside the governed runtime, where telemetry, retry,
timeout, and artifact policies already exist.

## Context Propagation

`ContextCarrier` is the shared state mechanism for composed skills.

It provides:

- layered writes instead of repeated ad-hoc dictionary copies
- deterministic snapshots for handler execution
- an audit trail for debugging orchestration flow

Typical propagated values include:

- `ask_result`
- `diagnosis_report`
- `corrective_action`
- `freeze_mode_state`
- execution metadata such as timeout and retry markers

## Decision Gates

Pipeline gates are configuration-driven.

Current gate source:

- `skill.config.pipeline.decision_gates` from the runtime registry
- `.providence/skills/sdd-pipeline/skill.yaml` as the canonical governance copy

Current supported rule:

- `diagnose_to_correct_min_confidence`

Default behavior:

- if diagnosis confidence is lower than the configured threshold, the pipeline
  skips `sdd-correct`
- if a stage fails, the pipeline exits early
- if freeze mode is enabled, the pipeline escalates immediately

## Retry and Timeout Semantics

Composed stages reuse the executor retry and timeout model.

- retryable command failures can be re-executed with backoff
- handler hooks can record retry or timeout-specific artifacts
- isolated stage timeouts return `policy_result="timeout"`
- pipeline stage timeouts escalate with `policy_result="pipeline_timeout"`

This distinction matters because a timed-out standalone skill is not equivalent
to a partially completed multi-stage remediation flow.

## Freeze Handling

Freeze mode is checked after each stage using propagated context.

When `freeze_mode_state.enabled` becomes true:

- the pipeline stops
- the result state becomes escalated
- the escalation reason records the stage that triggered the stop

This prevents downstream mutation after the runtime has detected an unsafe or
non-recoverable condition.

## Operational Notes

- Keep pipeline thresholds in skill config, not executor constants.
- Prefer adding stage-specific logic in handlers before extending executor
  branches.
- Validate new orchestration behavior with focused runtime tests before broader
  suite execution.

## References

- `docs/adr/ADR-013-pipeline-composition.md`
- `docs/adr/ADR-003-skill-handler-strategy-pattern.md`
- `docs/adr/ADR-004-skillengine-registry-executor-split.md`
- `.providence/skills/sdd-pipeline/skill.yaml`
