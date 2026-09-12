# Agent Entry Point

> **AI agents (Copilot, Claude, Gemini, etc.):** start here.

## Bootstrap Sequence

Load in this order when context is low:

1. This file
2. [docs/runtime/protocols/AGENT_ENTRYPOINT.md](../runtime/protocols/AGENT_ENTRYPOINT.md)
3. [docs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md](../runtime/protocols/AGENT_RUNTIME_PROTOCOL.md)

## Mandatory Mandates

| Mandate | File |
|---|---|
| M001 — Clean Architecture | [CLEAN_ARCHITECTURE.md](../spec/canonical/features/CLEAN_ARCHITECTURE.md) |
| M002 — TDD | [TDD.md](../spec/canonical/features/TDD.md) |

## Runtime Commands

```bash
providence runtime status --verbose    # check workspace health
providence governance compile          # build governance artifacts
providence governance score --verbose  # evaluate compliance
providence governance sign --help      # learn about mandatory human sign-off (P003)
sdd tools list                  # discover maintenance utilities
providence doctor run                  # full monorepo diagnostics
```

## Supervised Learning Commands

```bash
providence skills learning-candidates                       # derive rule candidates from failure ledger
providence skills learning-approve <candidate-id> --rationale "..." --ttl-days 30
providence skills learning-reject <candidate-id> --rationale "..."
providence skills learning-rules                            # list currently active rules
providence skills learning-impact <rule-id> \
  --rework-delta -0.10 \
  --false-block-rate 0.05 \
  --escalation-delta 0.02 \
  --rollback-flag
providence skills learning-status --window-days 7           # summary health for supervised learning
```

Operational policy:

- Rule activation is human-approved only.
- TTL expiration deactivates stale rules automatically.
- Negative learning (`--rollback-flag`) marks rule rollback in registry.

## Full Agent Protocol

See [docs/runtime/protocols/AGENT_ENTRYPOINT.md](../runtime/protocols/AGENT_ENTRYPOINT.md) for the complete operational guide including context loading strategy, anti-patterns, and decision models.
