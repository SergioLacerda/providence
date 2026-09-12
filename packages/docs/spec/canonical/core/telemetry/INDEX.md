# 📡 TELEMETRY — Runtime Observability & Audit

## 🎯 Purpose

Ensure 100% traceability of agentic decisions and governance compliance via structured telemetry and OpenTelemetry integration.

---

## 🔒 Invariants

Telemetry is:

- **Mandatory**: Every governance-aware action must be recorded.
- **Fail-Closed (Audit)**: If local persistence fails, the operation must be aborted.
- **Best-Effort (Export)**: External OTEL export is asynchronous and non-blocking.
- **Single Source of Truth**: The local `.providence/audit-trail/compliance-events.jsonl` is the canonical audit trail.

---

## 📊 Components

### 1. RuntimeEvent Envelope

A standardized data structure containing:

- **Trace Context**: `trace_id`, `span_id`.
- **Identity**: `workspace_id`, `agent_id`, `service`.
- **Governance**: `artifact_fingerprint`, `decision_source_refs`.
- **Economy**: Token counts, budget utilization, compression ratios.

### 2. TelemetrySink

The orchestrator for event collection and persistence:

- **Logging Modes**: `passive` (mandatory only), `active` (verbose), `strict` (audit-first).
- **Segmentation**: Ability to segment logs by `work_item_id` for task-scoped auditing.
- **Event Schemas**: Defined in [`governance-events.md`](governance-events.md).
- **Auto-Enrichment**: Derivation of economy metrics from raw byte counts.

### 3. OpenTelemetry (OTEL) Bridge

Mapping layer for industrial-grade observability:

- **Standard Mapping**: Translates SDD events into OTEL spans.
- **Namespace**: Uses `sdd.*` for all governance-specific attributes.
- **OTLP Export**: Native support for OTLP-HTTP/JSON exporters (Datadog, Grafana, Jaeger).

---

## 📜 Mandates

### M007: Telemetry Enforcement

Every agent interaction with the SDD framework MUST emit a `RuntimeEvent` via a `TelemetrySink`. Anonymous or unrecorded governance decisions are forbidden.

### M008: Audit Integrity

The local JSONL audit trail MUST be preserved and protected. Any attempt to modify or delete compliance logs without authorization is a critical security violation.

### M009: OTEL Compliance

When OpenTelemetry export is active, agents MUST provide valid `trace_id` and `span_id` headers to maintain the distributed trace continuity across the agentic ecosystem.

---

## ⚙️ Runtime Binding

- **Source**: `packages/core/providence_runtime/src/providence_runtime/telemetry.py`
- **OTEL Bridge**: `packages/core/providence_runtime/src/providence_runtime/otel.py`
- **Default Sink Path**: `.providence/audit-trail/compliance-events.jsonl`
