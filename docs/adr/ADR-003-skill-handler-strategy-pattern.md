# ADR-003 — Skill Handler Strategy Pattern

**Status:** Accepted
**Date:** 2026-05-19
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

`SkillEngine.run_skill` accumulated skill-specific logic in a single 277-line method, with cyclomatic complexity of 12 (suppressed via `# noqa: C901`). The pattern was:

```python
if skill.name == "sdd-ask":
    artifacts["execution_contract"] = ...
if skill.name == "sdd-diagnose":
    artifacts["diagnosis_report"] = ...
if skill.name == "sdd-correct":
    gate = ...
    if gate["decision"] != "allow":
        return early_result
# ... post-execution ...
if skill.name == "sdd-correct":
    learning.append_failure(...)
if skill.name == "sdd-converge":
    artifacts["convergence_delta_report"] = ...
```

Every new skill with lifecycle hooks required editing `run_skill` in 2–3 places. The open/closed principle was violated: `run_skill` was not closed for modification.

---

## Decision

**Use the Strategy pattern with optional lifecycle hooks per skill.**

Each skill with special pre/post execution logic gets a dedicated handler class. Handler classes have two optional methods:

- `pre_run(context, *, learning, skill, profile, footer_fn) -> PreRunOutcome` — runs before command execution; can return an early exit result
- `post_run(context, *, learning, exit_code, artifacts) -> dict[str, Any]` — runs after command execution; returns additional artifacts

Handler discovery uses a name-convention factory:

```
sdd-correct → "correct" → title-case → "Correct" → "CorrectHandler"
```

`run_skill` becomes a stable ~40-line template:

```
validate → policy check → deprecation → pre_run (if exists)
→ execute commands → post_run (if exists) → assemble result
```

**Registered handlers (2026-05-19):**

| Skill | Handler | Hooks |
|---|---|---|
| sdd-ask | `AskHandler` | `pre_run` (builds execution contract) |
| sdd-diagnose | `DiagnoseHandler` | `pre_run` (builds diagnosis report) |
| sdd-correct | `CorrectHandler` | `pre_run` (correction gate + early exit), `post_run` (learning + rule candidates) |
| sdd-converge | `ConvergeHandler` | `post_run` (convergence delta, rule decision, impact recording) |

---

## Consequences

**Positive:**

- Adding a new skill with lifecycle hooks = one new handler class, zero changes to `run_skill`
- `run_skill` cyclomatic complexity reduced from 12 to ~5; `# noqa: C901` removed
- Each handler is independently unit-testable without instantiating `SkillEngine`

**Negative:**

- Handler discovery via `globals()` is implicit — a developer must know the naming convention to find `CorrectHandler`

**Files:**

- `packages/core/providence_runtime/src/providence_runtime/_skill_executor.py` — handlers + `_get_skill_handler` factory
- `packages/core/providence_runtime/tests/test_skill_handler_correct.py` — handler unit tests
