> Layer: runtime - operational agent instructions

# AI Agent Entry Point

Operational guide for Copilot and other agents acting in this workspace under SDD governance.

## Minimal bootstrap (when context is low)

Load in this order:

1. **`.providence/agent-instructions.md`** ← Primary governance source (mandates + self-evaluation)
2. [docs/guides/TECHNICAL_GUIDE.md](../../guides/TECHNICAL_GUIDE.md)
3. [docs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md](./AGENT_RUNTIME_PROTOCOL.md)

---

## Mandatory mandates

The file `.providence/agent-instructions.md` provides the **mandate index with micro-descriptions**.

| Mandate | Summary | Full details (on demand) |
|---------|--------|----------------------------------|
| M001 — Clean Architecture | Mandatory layers, no cross imports | [CLEAN_ARCHITECTURE.md](../../spec/canonical/features/CLEAN_ARCHITECTURE.md) |
| M002 — TDD | Coverage > 80%, pytest, mocks only in infra | [TDD.md](../../spec/canonical/features/TDD.md) |
| M003 — Context Awareness | On-demand reading, minimal context | `docs/spec/canonical/core/mandates/M003_CONTEXT_AWARENESS.md` |

> **On-demand reading pattern:** Read the index in `.providence/agent-instructions.md`. If the mandate summary is **not** sufficient for your current task → make a tool call to read the full details in the reference file above.

## SELF-EVALUATION (mandatory self-assessment)

Before executing any action in the workspace:

- **Confident** that the action respects the mandates listed above → **Proceed.**
- **NOT confident** or unsure about the technical details → **Read `.providence/compiled/governance-core.json` before continuing.**

## Strict Auto-Fix Hygiene (Mandatory)

```bash
ruff check --fix .
ruff format .
ruff check .
mypy .
pytest
```

Post auto-fix revalidation is mandatory before delivery.

## Additional navigation

- Master navigation: [docs/guides/TECHNICAL_GUIDE.md](../../guides/TECHNICAL_GUIDE.md)
- Cognition and decision models: `docs/cognition/INDEX.md`
- Runtime protocol: [docs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md](./AGENT_RUNTIME_PROTOCOL.md)
