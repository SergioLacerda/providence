# Mandate: Governance Federation

**ID:** M019
**Type:** MANDATE
**Enforcement:** HARD
**Required:** true
**Phase:** pre-execution

---

## Objective

Define how any plugin or skill declares identity, negotiates capabilities,
and adheres to host governance before execution inside an SDD-governed
environment.

---

## Requirements

1. Plugins MUST perform a governance handshake before execution
2. Handshake MUST declare: id, version, risk, capabilities, governance.mode, must_follow
3. Plugins MUST NOT override host governance silently
4. Plugins MUST NOT invent SDD rules that do not exist
5. Plugins MUST stop or degrade safely when governance context is missing
6. Plugins operating in governed mode MUST respect all HARD mandates
7. Internal SDD skills (under `.providence/skills/`) MUST declare `governance_adherence:` in skill.yaml
8. External plugins are registered via `.providence/plugins/registry.yaml` through agent-mediated handshake
9. GovernanceEvent MUST be emitted on registration: `type=PLUGIN_REGISTERED`
10. GovernanceEvent MUST be emitted on violation: `type=PLUGIN_GOVERNANCE_VIOLATION`

---

## Integration Modes

| Mode | Condition | Behavior |
|------|-----------|----------|
| `governed` | Full `.providence/` governance found | HARD mandates enforced, execution contract required, artifacts validated |
| `compatible` | Partial governance found | Adapts to available rules, reports missing context, degrades safely |
| `standalone` | No governance found | Read-only by default, produces portable artifacts, recommends SDD integration |

---

## Enforcement

Agent-mediated registration writes entries to `.providence/plugins/registry.yaml`.
See `.providence/plugins/handshake-protocol.md` for the full registration flow.

Internal skills declare adherence explicitly in `skill.yaml`:

```yaml
governance_adherence:
  mode: governed
  respects_hard_mandates: true
  must_follow:
    - M017
    - M019
```

---

## Rationale

M017 covers execution enforcement (write scope, execution_provider, approval_gate) for
analysis plugins. M019 covers the federation layer: how any plugin enters the governance
environment, declares its contract, and negotiates operating mode. Together they ensure
plugins are both correctly declared (M019) and correctly constrained at runtime (M017).

---

## Enforcement Steps

- Verify plugin has performed governance handshake before execution
- Verify registry entry exists for plugin in `.providence/plugins/registry.yaml` (external) or `governance_adherence:` block in `skill.yaml` (internal)
- Verify plugin respects all HARD mandates when mode=governed
- Verify GovernanceEvent emitted on registration and on violation
- Verify internal skills declare `governance_adherence:` in their skill.yaml

---

## Related

- M017: Analysis Plugin Compliance (execution enforcement, downstream)
- M015: Bidirectional Agent Handshake (complementary handshake contract)
- M016: Guardrail Non-Regression (applies to plugin-produced artifacts)
- `.providence/plugins/registry.yaml` (external plugin registry)
- `.providence/plugins/plugin-entry.schema.yaml` (registry entry schema)
- `.providence/plugins/handshake-protocol.md` (registration flow)
