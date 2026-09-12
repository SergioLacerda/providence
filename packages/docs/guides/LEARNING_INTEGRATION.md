# Learning Integration Guide

This guide describes how supervised learning is integrated into the governed
runtime today.

It focuses on the runtime-side feedback loop implemented in
`packages/core/providence_runtime/src/providence_runtime/learning.py` and consumed by skill
handlers in `packages/core/providence_runtime/src/providence_runtime/_skill_executor.py`.

## Scope

The current learning flow covers four runtime concerns:

- recording execution outcomes in the failure ledger
- injecting recent operational history into `sdd-ask`
- calibrating `sdd-diagnose` confidence from recurring failures
- promoting recurring patterns into human-approved rule candidates

This is runtime guidance. Command syntax remains canonical in
`docs/spec/reference/commands/cli.md`.

## Storage Model

`SupervisedLearningStore` persists learning artifacts under `.providence/runtime/`.

Current files:

- `.providence/runtime/failure-ledger.jsonl`
- `.providence/runtime/rule-candidates.json`
- `.providence/runtime/rule-registry.json`
- `.providence/runtime/rule-impact.jsonl`

The store is append-oriented for event history and JSON-backed for mutable rule
state.

## Runtime Flow

The feedback loop is intentionally asymmetric:

1. `sdd-ask` reads recent failures and active rules before execution.
2. `sdd-diagnose` looks for similar failures and adjusts confidence.
3. `sdd-correct` records outcomes and derives rule candidates from recurrence.
4. `sdd-converge` records rule decisions and rule impact metrics.

This keeps the early stages context-aware without allowing automatic rule
creation or activation.

## Ask Integration

`AskHandler.pre_run()` enriches the execution contract with historical context
when learning data is available.

Current inputs:

- `learning.list_failures(limit=3)`
- `learning.list_active_rules()`

Current output shape:

- `execution_contract["historical_context"]["recent_failures"]`
- `execution_contract["historical_context"]["active_rules"]`

This gives `sdd-ask` a small, bounded memory of recent operational failures and
already-approved guardrails without expanding the runtime contract into an
unbounded history dump.

`AskHandler.post_run()` also records the ask execution in the ledger so the
learning loop includes input-stage behavior, not only downstream correction.

## Diagnose Integration

`DiagnoseHandler.pre_run()` builds a diagnosis report, then checks for
recurrence via `learning.find_similar_failures(...)`.

When similar failures exist:

- recurrence count is added to the diagnosis artifacts
- confidence is calibrated upward using the observed recurrence rate
- calibrated confidence is capped at `1.0`

This means diagnosis confidence is no longer purely local to the current run; it
can reflect historical confirmation of the same symptom pattern.

`DiagnoseHandler.post_run()` records the diagnosis outcome and preserves any
`evidence_refs` produced by the diagnosis report.

## Correction And Rule Lifecycle

`sdd-correct` and `sdd-converge` close the loop.

`CorrectHandler` uses the learning store to:

- record denied or executed corrections in the failure ledger
- generate `RuleCandidate` entries from repeated symptom/root-cause pairs

`ConvergeHandler` uses the learning store to:

- approve or reject candidates through explicit rule decisions
- record impact metrics for active rules
- roll back rules when negative learning is reported

This split is deliberate:

- correction discovers patterns
- convergence decides whether the discovered pattern should become policy

## Human Approval Boundary

Learning does not auto-activate rules.

The safe default workflow is:

1. runtime accumulates repeated failures
2. operators inspect candidates with `providence skills learning-candidates`
3. a human approves or rejects each candidate
4. runtime tracks impact of approved rules
5. negative impact can roll the rule back

This preserves governance requirements around human review and prevents silent
self-modifying behavior.

## Operational Queries

Use these commands when inspecting the learning loop:

```bash
uv run providence skills learning-status --window-days 7
uv run providence skills learning-candidates
uv run providence skills learning-rules
uv run providence skills run sdd-ask
uv run providence skills run sdd-diagnose
```

For approval and impact recording, keep using the canonical CLI workflow from
`docs/spec/reference/commands/cli.md`.

## Design Constraints

- Keep historical context bounded; `sdd-ask` only loads a small recent window.
- Keep rule activation human-approved; runtime may suggest, not self-authorize.
- Keep evidence references attached to diagnosis and correction artifacts.
- Keep runtime storage local to `.providence/runtime/` for auditability and teardown.

## References

- `packages/core/providence_runtime/src/providence_runtime/learning.py`
- `packages/core/providence_runtime/src/providence_runtime/_skill_executor.py`
- `docs/architecture/c4-components-runtime.md`
- `docs/spec/reference/commands/cli.md`
- `docs/guides/AGENT_GUIDE.md`
