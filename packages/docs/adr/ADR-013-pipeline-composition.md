# ADR-013 — Python-Native Pipeline Composition for Governed Skills

**Status:** Accepted
**Date:** 2026-06-11
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

The governed `sdd-pipeline` flow originally existed as a registry entry plus CLI
fallback commands, but not as a first-class runtime composition model.

That left three structural gaps in `packages/core/providence_runtime/src/providence_runtime/_skill_executor.py`:

1. Cross-stage state moved only through ad-hoc plain dictionaries, making it
   harder to preserve provenance and audit context propagation.
2. `sdd-pipeline` could list its stages, but could not express runtime decision
   gates such as "skip correction when diagnosis confidence is too low".
3. Timeout, freeze-mode, and retry behavior existed per isolated skill
   execution, but not as an orchestration contract spanning ask → diagnose →
   correct → converge.

The pending implementation roadmap in
`.analysis/pending/providence_cli_skills/05-IMPLEMENTATION_ROADMAP.md` explicitly
called for a composed runtime pipeline, a context carrier, freeze escalation,
retry/timeout hooks, and externalized gate rules.

---

## Decision

Implement governed skill composition directly inside the runtime executor using
four coordinated decisions:

- Introduce `ContextCarrier` as the mutable orchestration state passed across
  pipeline stages, with snapshot and audit-trail support.
- Allow handlers to request composition through `PreRunOutcome(compose=True, ...)`
  instead of forcing every skill to execute through CLI fallback commands.
- Model `sdd-pipeline` as a Python-native pipeline that runs `sdd-ask`,
  `sdd-diagnose`, `sdd-correct`, and `sdd-converge` sequentially inside the
  executor.
- Externalize pipeline decision gates into skill configuration
  (`skill.config.pipeline.decision_gates`) so orchestration thresholds are data,
  not hard-coded control flow.

`PipelineHandler` owns stage validation and composition setup. `SkillExecutor`
owns execution of the composed stages, propagation of shared context, early
termination rules, timeout escalation, retry bookkeeping, and freeze-mode exit.

---

## Consequences

**Positive:**

- `sdd-pipeline` becomes a real runtime orchestration primitive instead of a
  thin CLI indirection layer.
- Ask results and diagnosis artifacts propagate predictably between stages using
  one context carrier instead of repeated `dict.copy()` patterns.
- Decision gates are testable and tunable through config, allowing future
  thresholds without reworking executor internals.
- Timeout, retry, and freeze-mode behavior now produce consistent pipeline-level
  artifacts and escalation states.
- Additional orchestrated skills can reuse the same composition mechanism.

**Negative:**

- `_skill_executor.py` now owns more orchestration semantics and must preserve
  clear boundaries between isolated skill execution and composed pipeline logic.
- Handler contracts are richer (`pre_run`, `post_run`, `timeout_hook`,
  `retry_hook`, `can_retry`), increasing the review surface for new skills.
- Pipeline correctness now depends on both code and canonical skill config
  remaining aligned.

---

## Alternatives Considered

- **Keep `sdd-pipeline` as CLI-only orchestration.** Rejected because runtime
  policies such as gates, retry metadata, and freeze escalation would remain
  fragmented across shell commands instead of governed Python contracts.
- **Create a separate pipeline engine module first.** Rejected for now because
  the existing `SkillExecutor` already owns the execution template and is the
  narrowest place to add composition without new public surface area.
- **Hard-code gate thresholds in `PipelineHandler`.** Rejected because the
  roadmap explicitly called for externalized gate rules and tests benefit from
  data-driven thresholds.

---

## Links

- `packages/core/providence_runtime/src/providence_runtime/_skill_executor.py`
- `packages/core/providence_runtime/src/providence_runtime/_skill_contracts.py`
- `packages/core/providence_runtime/src/providence_runtime/skills.py`
- `.providence/skills/sdd-pipeline/skill.yaml`
- `docs/guides/PIPELINE_ORCHESTRATION.md`
- `.analysis/pending/providence_cli_skills/05-IMPLEMENTATION_ROADMAP.md`
