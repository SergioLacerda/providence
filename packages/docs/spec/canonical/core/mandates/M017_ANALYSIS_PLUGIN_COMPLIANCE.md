# Mandate: Analysis Plugin Compliance

**ID:** M017
**Type:** MANDATE
**Enforcement:** HARD
**Required:** true
**Phase:** pre-execution

---

## Objective

Ensure that analysis plugins respect SDD-injected base_path, execution_provider, and approval_gate.

---

## Requirements

1. Plugins MUST write artifacts only within sdd_injection.base_path
2. Plugins MUST invoke only the declared sdd_injection.execution_provider
3. Plugins MUST not skip sdd_injection.approval_gate when set to required
4. Plugin registry entries MUST declare all three sdd_injection fields: base_path, execution_provider, approval_gate
5. Violations MUST emit a GovernanceEvent with event_type=PLUGIN_COMPLIANCE_VIOLATION

---

## Enforcement

The `sdd plugin validate` command enforces the registry declaration requirement.
Runtime violations emit `GovernanceEvent` with `severity=critical` to
`.providence/audit-trail/compliance-events.jsonl`.

---

## Rationale

Plugins extend SDD with external orchestration capabilities. Without governance over
their write scope and execution authority, a plugin could silently corrupt the
workspace or bypass approval controls. M017 ensures the plugin contract is
enforceable and auditable.

---

## Enforcement Steps

- Verify plugin registry entry declares sdd_injection with base_path, execution_provider, approval_gate
- Verify plugin does not write outside sdd_injection.base_path
- Verify plugin invokes only the declared execution_provider
- Verify approval_gate is honored when set to required
- Confirm GovernanceEvent emitted on any plugin compliance violation

---

## Related

- M010: Delivery Hygiene Enforcement
- M016: Guardrail Non-Regression
- `.providence/plugins/registry.yaml` (plugin registry)
- `.providence/contracts/analysis-provider.schema.yaml` (plugin contract schema)
