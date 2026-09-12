# Mandate: Audit Integrity

**Type:** HARD MANDATE
**ID:** M008
**Category:** Security / Compliance / Audit Trail
**Enforced By:** Pre-commit hooks, CI/CD gates, runtime validation

---

## 🎯 Goal

Preserve and protect the integrity of the audit trail (`.providence/audit-trail/compliance-events.jsonl`) to ensure forensic capability, regulatory compliance, and accountability for all governance-aware actions.

---

## 📜 Requirement

**HARD RULE:** The local JSONL audit trail MUST be preserved and protected at all times.

### What is Protected

- **`.providence/audit-trail/compliance-events.jsonl`** — Append-only JSONL containing all governance events
- **Event Schema** — Format and field definitions (see [`governance-events.md`](../telemetry/governance-events.md))
- **Timestamps** — Original event emission times (never modified retroactively)
- **Authorship** — Who/what agent triggered each event (never falsified)

### Operations Prohibited

- ❌ Modifying existing events in the log
- ❌ Deleting events without authorization
- ❌ Reordering events (breaks temporal causality)
- ❌ Falsifying timestamps
- ❌ Anonymizing events to hide violations

### Operations Required

- ✅ Appending new events (only way to modify log)
- ✅ Archiving old logs (with retention policy)
- ✅ Verifying log integrity before key operations
- ✅ Backing up logs for disaster recovery
- ✅ Monitoring log growth and storage capacity

---

## ⚖️ Rationale

- **Forensics:** If governance fails, we must be able to replay and understand what happened
- **Compliance:** Regulators (GDPR, SOC2) require immutable audit trails
- **Accountability:** Agents must not be able to hide violations after the fact
- **Detection:** Unusual patterns visible only in unmodified logs

---

## 🔒 Validation

Before merge:

- [ ] `.providence/audit-trail/compliance-events.jsonl` exists and is append-only
- [ ] No manual editing of compliance events (only appends)
- [ ] Log is backed up in `.git/` or external secure storage
- [ ] CI/CD validates log format (valid JSONL, no corruption)

---

## 🚨 Violations

| Violation | Severity | Resolution |
|---|---|---|
| Modifying past event | 🔴 CRITICAL | Revert file to last known good; escalate to security team |
| Deleting events | 🔴 CRITICAL | Restore from backup; audit who/why; disable agent access |
| Log file missing | 🔴 CRITICAL | Stop all work; investigate data loss; notify compliance |
| Invalid JSON in log | 🟠 HIGH | Fix schema; regenerate if corrupted; audit cause |

---

## 🔧 Implementation

**Runtime:**

- All events persisted via `TelemetrySink` to `.providence/audit-trail/compliance-events.jsonl` (append-only mode)
- Pre-commit hook validates log format before commit
- CI/CD gate prevents merge if log modified incorrectly

**Archival:**

- Old logs archived with timestamp: `compliance-events-2026-05-01.jsonl.gz`
- Retained per data retention policy (recommend: 2 years minimum)
- Archived logs treated with same protection as current log

---

## Enforcement Steps

- Verify `.providence/audit-trail/compliance-events.jsonl` exists and has not been modified (only appended)
- Confirm no events have been deleted, reordered, or had timestamps altered
- Confirm all new governance events were appended (never overwritten) to the log
- Confirm log format is valid JSONL with no corrupted entries
- Verify log file is backed up per the data retention policy

---

## 🔗 Related

- [M007: Telemetry](M007_TELEMETRY.md) — Mandatory event emission
- [M009: OTEL Compliance](M009_OTEL_COMPLIANCE.md) — Distributed trace integrity
- [governance-events.md](../telemetry/governance-events.md) — Event schema definitions
- [P003: Mandatory Human Review](../policies/P003_MANDATORY_HUMAN_REVIEW.md) — Who approves audit operations
