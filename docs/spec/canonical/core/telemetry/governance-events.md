# 📑 Governance Events — Runtime Event Schema

## 🎯 Purpose

Define the normative schema for governance-specific events that are not related to token economy. These events track the health, compliance, and authority boundaries of the agentic system.

---

## 🔒 Mandatory Event Set

These events MUST be emitted by the framework and MUST be persisted regardless of the `logging_mode`.

| Event | Status | Trigger Condition |
|-------|--------|-------------------|
| `runtime.session.start` | `ok` | Agent session initialization |
| `runtime.drift.detected` | `warn` | Mismatch between session state and compiled artifact |
| `governance.violation` | `fail` | Attempt to bypass or violate a HARD MANDATE |
| `policy.validation.fail` | `fail` | Failure to meet a POLICY constraint |

---

## 📊 Event Specific Details

### `runtime.drift.detected`

Tracks when an agent is operating with stale or mismatched governance artifacts.

- **`details.drift_type`**: `fingerprint_mismatch` | `schema_version_mismatch` | `mandate_missing`.
- **`details.remediation_command`**: The command the user must run to fix the drift.

### `governance.violation`

The most critical audit signal. Indicates an active breach of the authority boundary.

- **`details.mandate_id`**: The ID of the mandate being violated (e.g., `M001`).
- **`details.violation_type`**: `unauthorized_mutation` | `unauthorized_network_call` | `path_bypass`.
- **`details.severity`**: Always `CRITICAL`.

### `governance.ask`

Tracks every query made to the SDD context loading engine.

- **`details.query`**: The intent/topic being loaded.
- **`details.max_items`**: The limit requested by the agent.
- **`details.items_returned`**: Count of items actually loaded.

---

## 🔭 OTEL Mapping

Governance events are exported under the `sdd.*` namespace.

| RuntimeEvent Field | OTEL Key |
|--------------------|----------|
| `artifact_fingerprint` | `sdd.artifact_fingerprint` |
| `decision_source_refs` | `sdd.decision_source_refs` |
| `level` | `sdd.level` |
| `status` | `sdd.status` |

---

## 🔗 References

- Envelope definition: [`INDEX.md`](INDEX.md)
- Economy metrics: [`../economy/metrics.md`](../economy/metrics.md)
- Drift detection logic: `packages/core/providence_runtime/src/providence_runtime/drift.py`
