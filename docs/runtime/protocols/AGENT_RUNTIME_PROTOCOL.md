> Layer: runtime - operational agent instructions

# Agent Runtime Protocol

Mandatory operational protocol for any AI agent executing tasks in this workspace.

## 7-Phase Flow

All work — bug fix, feature, refactor, documentation — follows this flow. It is not optional.

```
PHASE 0: Check context and initial state
   ↓
PHASE 1: Load rules and mandates
   ↓
PHASE 2: Check execution state (detect conflicts)
   ↓
PHASE 3: Choose path: bug=A | simple=B | complex=C | multi=D
   ↓
PHASE 4: Load task-specific context
   ↓
PHASE 5: Implement (code + tests, TDD)
   ↓
PHASE 6: Validate (tests + definition of done)
   ↓
PHASE 7: Checkpoint (document + deliver)
```

## Mandatory commands per phase

### Phase 0 — Initial state

```bash
providence runtime status --verbose   # Check workspace health
providence governance validate        # Confirm governance integrity
```

### Phase 1 — Rules and mandates

**Mandatory bootstrap:** Read `.providence/agent-instructions.md` first.
It contains the mandate index with micro-descriptions and the **SELF-EVALUATION** block.

- ✅ Confident with the summaries → Proceed directly.
- ❌ Not confident → Read the details on demand:
  - [M001](../../spec/canonical/features/CLEAN_ARCHITECTURE.md) — Clean Architecture
  - [M002](../../spec/canonical/features/TDD.md) — Mandatory TDD
  - `M003` — see `docs/spec/canonical/core/mandates/M003_CONTEXT_AWARENESS.md`

### Phase 5 — Implementation

```bash
providence test run          # Run tests on every significant change
providence lint run          # Lint before declaring done
```

### Phase 6 — Final validation

```bash
providence test run                    # Full suite
providence lint run                    # Static quality
providence governance validate         # Governance integrity
providence runtime status --verbose    # Final workspace state
```

## Context management (LLM memory)

| Phase | What to load | Purpose |
|------|---------------|-----------|
| Planning | `docs/cognition/decision-models/` | Assess risk and confidence |
| Execution | `docs/cognition/decision-models/TASK_CLASSIFICATION.md` | Select the appropriate PATH (A-F) |
| Operational failure or diagnosis | `docs/runbooks/README.md` -> one selected runbook leaf | Reuse a known procedure without loading all runbooks |
| Validation | `docs/spec/canonical/specifications/definition_of_done.md` | Quality criteria |

> Never load the entire documentation. Always use path-based context loading via the Master Index.
> Runbooks are selected from authored `docs/` sources and compiled into runtime
> handbook output. Do not edit `.providence/` directly to change runbook behavior.

## References

- Entrypoint: [AGENT_ENTRYPOINT.md](./AGENT_ENTRYPOINT.md)
- CLI Reference: [docs/spec/reference/commands/cli.md](../../spec/reference/commands/cli.md)
- Master navigation: [docs/guides/TECHNICAL_GUIDE.md](../../guides/TECHNICAL_GUIDE.md)
- Definition of Done: `docs/spec/canonical/specifications/definition_of_done.md`
- Operational PATHs: `docs/runtime/paths/`
