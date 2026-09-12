# Plugin Registration Protocol

**Status:** Active
**Mandate:** M019 (Governance Federation)
**Agent-facing counterpart:** `.providence/plugins/handshake-protocol.md`

---

## Overview

Plugin registration is **agent-mediated**: the agent detects Providence governance,
identifies the active skill, and offers to register it. The user approves.
The agent writes the entry to `.providence/plugins/registry.yaml` and emits a
GovernanceEvent.

No plugin self-registers. No static pre-population. The registry reflects
what has actually been used and approved in this project.

---

## Registration Flow

```
Agent detects .providence/metadata.json
        ↓
Agent identifies active skill
        ↓
Agent checks registry.yaml for existing entry
        ↓ (not found)
Agent offers registration to user
        ↓ (user approves)
Agent extracts data from skill.yaml
        ↓
Agent determines governance mode
  (governed / compatible / standalone)
        ↓
Agent validates entry against plugin-entry.schema.yaml
        ↓
Agent writes entry to registry.yaml
        ↓
GovernanceEvent emitted: PLUGIN_REGISTERED
```

---

## Governance Mode Determination

The agent determines mode based on what governance it finds at registration time:

| Condition | Mode assigned |
|-----------|--------------|
| `.providence/metadata.json` present + all HARD mandates resolvable | `governed` |
| `.providence/metadata.json` present but governance incomplete | `compatible` |
| No `.providence/` found | `standalone` (registration deferred) |

---

## Re-registration

If an entry for the same plugin `id` already exists:

1. Agent shows the existing entry
2. Agent asks: "Entry for `<id>` already exists. Update or skip?"
3. Update: entry is replaced, `registered_at` updated
4. Skip: no change made

The agent MUST NOT silently overwrite an existing entry.

---

## GovernanceEvents

Two events are relevant to plugin governance:

| Event type | When emitted | Severity |
|------------|-------------|---------|
| `PLUGIN_REGISTERED` | Plugin successfully registered | `info` |
| `PLUGIN_GOVERNANCE_VIOLATION` | Plugin violated M019 or M017 at runtime | `critical` |

Events are written to `.providence/runtime/compliance-events.jsonl`.

---

## Internal Skills

Skills under `.providence/skills/` are **not registered** via this protocol. Their
governance contract is declared directly in their `skill.yaml` via the
`governance_adherence:` block. They are governed at load time, not registration time.

See [Plugin Governance Overview](plugin-governance-overview.md) for the two-tier model.
