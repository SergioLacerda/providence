# Mandate: Telemetry Enforcement

**Type:** HARD MANDATE
**ID:** M007
**Category:** Observability / Audit

---

## 🎯 Goal

Ensure 100% traceability of agentic decisions and governance compliance via structured telemetry and OpenTelemetry integration.

---

## 📜 Requirement

Agents MUST record every interaction with the SDD framework and every governance-aware decision.

### Mandatory Events

Every agent session MUST emit the following events at a minimum:

- `runtime.session.start`: Emitted when the agent initializes.
- `governance.ask`: Emitted when querying the context loader.
- `governance.violation`: Emitted when a mandate breach is detected.
- `economy.budget.breach`: Emitted when the context budget is exhausted.

### OTEL Traceability

If OpenTelemetry is enabled, agents MUST:

1. Provide a unique `trace_id` for each root task.
2. Provide a unique `span_id` for each sub-task or framework call.
3. Map all governance metadata to the `sdd.*` attribute namespace.

---

## 🛠️ Implementation

- **Runtime module:** `packages/core/providence_runtime/src/providence_runtime/telemetry.py`
  - `RuntimeEvent` — standardized event envelope.
  - `TelemetrySink` — collector and JSONL persistence.
- **OTEL Bridge:** `packages/core/providence_runtime/src/providence_runtime/otel.py`
  - `OtelBridge` — subclass for OTEL export.
  - `OtlpHttpExporter` — OTLP-HTTP/JSON transport.

---

## ⚖️ Rationale

Unrecorded governance decisions are a security risk. Telemetry provides the "black box" required to debug agent failures, audit compliance breaches, and optimize token economy efficiency across the entire ecosystem.

---

## ✅ Validation

- [ ] Every `providence ask` command generates at least one entry in `.providence/compliance-events.jsonl` (written to the runtime state folder).
- [ ] Events contain a valid `artifact_fingerprint`.
- [ ] If an OTEL endpoint is configured, spans appear in the target observability platform with `sdd.*` attributes.

---

## Skill-Oriented Reinforcement (Normative)

- [ ] Every `providence skills run <skill>` invocation MUST emit a structured skill execution event.
- [ ] Skill telemetry MUST include at minimum: skill name, active profile, policy result, reason, and exit code.
- [ ] If CLI primitive fallback is used, telemetry MUST include fallback command references for forensic traceability.

---

## Enforcement Steps

- Confirm `runtime.session.start` event was emitted at agent initialization
- Confirm `governance.ask` event is emitted on every SDD context query
- Confirm `governance.violation` event is emitted when any mandate breach is detected
- Confirm `economy.budget.breach` event is emitted when context budget is exhausted
- If OpenTelemetry is active, verify each root task has a unique `trace_id` and each sub-task has a unique `span_id`
- Verify all governance metadata is mapped under the `sdd.*` OTEL attribute namespace

---

## References

- Envelope definition: [`telemetry/INDEX.md`](../telemetry/INDEX.md)
- Metric definitions: [`economy/metrics.md`](../economy/metrics.md)
