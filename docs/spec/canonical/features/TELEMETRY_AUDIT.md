---
governance_source:
  id: DOC-TELEMETRY-AUDIT
  type: feature
  status: active
  title: Telemetry and Audit Trail
  refs: [M007, M008, M009]
  publication: published
---

# Feature: Telemetry & Audit Trail

**Type:** CORE FEATURE
**Governance refs:** M007, M008, M009
**Category:** Observability

---

## 🎯 Goal

Provide an industrial-grade, immutable audit trail of all agentic decisions, ensuring accountability and real-time monitoring of governance compliance.

---

## 📜 Requirement

The system MUST implement a dual-sink telemetry architecture:

1. **Local Audit Trail (Canonical)**:
    * Structured JSONL events persisted to `.providence/audit-trail/compliance-events.jsonl`.
    * Mandatory persistence for all governance violations and budget breaches.
    * Support for task-scoped segmentation (work-item segmentation).

2. **OpenTelemetry Bridge (Global)**:
    * Asynchronous export of events to any OTLP-compliant backend.
    * Standardized `sdd.*` attribute mapping for governance metrics.
    * Zero-dependency implementation using Python standard library.

---

## ⚖️ Rationale

In autonomous agent systems, "black box" behavior is a catastrophic risk. This feature ensures that every decision point is recorded with its associated governance context (fingerprint, mandates loaded, budget state), making every agent action auditable and transparent.

---

## ✅ Validation

* [ ] Every agent command emits a `runtime.session.start` event.
* [ ] Budget breaches (≥100%) trigger an immediate `economy.budget.breach` event.
* [ ] Trace IDs are propagated across the session to link related operations.
* [ ] Events successfully export to OTEL backends when configured.

---

## 📊 Learning Signals Contract

`providence ask` derives a `learning_signals` block from the audit trail defined above
(`.providence/runtime/failure-ledger.jsonl` and `.providence/runtime/compliance-events.jsonl`)
and includes it in every JSON response (`data.learning_signals`).

### Fields

| Field | Meaning | Source |
|-------|---------|--------|
| `observed_events` | Total rows scanned within `window_days` across both sinks. | failure-ledger + compliance-events |
| `diagnosis_inconclusive` | Failure-ledger entries whose `root_cause == "diagnosis.inconclusive"`. | failure-ledger |
| `evidence_insufficient` | Failure-ledger entries whose `root_cause == "evidence.insufficient"`. | failure-ledger |
| `scope_violation` | Failure-ledger entries whose `root_cause == "scope.violation"`. | failure-ledger |
| `drift_recent_failures` | Compliance events with `status` in `{warn, fail, error}`. | compliance-events |
| `window_days` | Rolling window size in days (default 7). | configuration |

### Consumption contract for governed agents

* `learning_signals` is **informational only**. It MUST NOT be used to derive
  `execution_gate` — that decision is governed exclusively by
  `intake_index_mode` and `hard_mode_invariants` (see `.providence/skills/sdd-ask/skill.yaml`).
* When `inputs.full` is set (`providence ask --full`) or any signal count is non-zero,
  the agent SHOULD surface the non-zero signals to the user as a recommendation
  (e.g. "scope_violation: 2 in the last 7 days — review recent failure-ledger entries").
* `scope_violation > 0` and `drift_recent_failures > 0` SHOULD be treated as a
  prompt for the agent to re-read `.providence/runtime/failure-ledger.jsonl` /
  `.providence/runtime/compliance-events.jsonl` before proposing further changes in the
  same area, but MUST NOT by themselves trigger `requires_human_review` or
  `escalate_to_human` — those remain governed by `escalation_policy.require_human_on`
  (`drift.critical`, `governance.violation`, `contract.invalid`).
* `observed_events == 0` means the window has no data (e.g. fresh workspace) and
  carries no signal — agents MUST NOT treat it as a degraded or drift condition.
