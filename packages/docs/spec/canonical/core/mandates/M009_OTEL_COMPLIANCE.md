# Mandate: OpenTelemetry Compliance

**Type:** HARD MANDATE
**ID:** M009
**Category:** Observability / Distributed Tracing / Integration
**Enforced By:** Runtime validation, CI/CD gates

---

## 🎯 Goal

Maintain distributed trace continuity across the agentic ecosystem by enforcing valid OpenTelemetry (OTEL) context propagation on all governance-aware operations.

---

## 📜 Requirement

**HARD RULE:** When OpenTelemetry export is active, agents MUST provide valid `trace_id` and `span_id` headers to maintain distributed trace continuity.

### What Must Be Provided

Every agentic operation MUST include:

- **`trace_id`** (UUID format, 16 hex bytes) — Unique trace identifier
- **`span_id`** (UUID format, 8 hex bytes) — Unique span within the trace
- **`trace_state`** (optional) — Vendor-specific trace state
- **`parent_span_id`** (if not root) — Parent span reference for causality

### Context Propagation Headers

```http
traceparent: 00-<trace_id>-<span_id>-<trace_flags>
tracestate: <vendor-specific>
```

Example:

```http
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
tracestate: dd=s:1
```

### Namespace Convention

All SDD-specific OTEL attributes use the `sdd.*` namespace:

```
sdd.workspace_id
sdd.agent_id
sdd.service
sdd.decision_source
sdd.artifact_fingerprint
sdd.budget_utilization_pct
sdd.compression_ratio
```

---

## ⚖️ Rationale

- **Distributed Tracing:** Multi-agent systems need to correlate work across agents and services
- **Compliance:** Audit trails must show causality across system boundaries
- **Debugging:** When issues arise, need to trace through the full decision chain
- **SLA Monitoring:** Correlate latency and errors across services

---

## 🔒 Validation

Before operation:

- [ ] `trace_id` is present and valid UUID format
- [ ] `span_id` is present and valid UUID format
- [ ] Parent span reference is correct (if not root trace)
- [ ] `sdd.*` attributes populated with governance context
- [ ] OTEL exporter is reachable (if configured)

**Failure Mode:**

- If validation fails and OTEL is mandatory → BLOCK operation and escalate
- If OTEL is optional → WARN and proceed with local telemetry only

---

## 🚨 Violations

| Violation | Severity | Resolution |
|---|---|---|
| Missing trace_id | 🔴 CRITICAL | Generate new trace; warn agent; escalate if repeated |
| Invalid trace_id format | 🔴 CRITICAL | Reject operation; return error to agent |
| Missing span_id | 🔴 CRITICAL | Generate new span; warn agent |
| Trace context lost between hops | 🟠 HIGH | Document break; investigate causality gap |
| OTEL exporter unreachable | 🟡 MEDIUM | Fall back to local-only telemetry; alert ops |

---

## 🔧 Implementation

**Runtime:**

- `OtelBridge` class translates SDD events to OTEL spans
- `OtlpHttpExporter` sends spans to configured OTLP receiver
- `TelemetrySink` enriches events with trace context before persistence

**Configuration:**

```bash
# Via environment
SDD_OTEL_ENABLED=true
SDD_OTEL_ENDPOINT=http://localhost:4318  # OTLP HTTP endpoint
SDD_OTEL_SERVICE_NAME=sdd-agent
```

**Code Pattern:**

```python
from providence_runtime.otel import OtelBridge

bridge = OtelBridge(service_name="providence")
with bridge.start_span("task.execute") as span:
    span.set_attribute("sdd.workspace_id", workspace_id)
    span.set_attribute("sdd.agent_id", agent_id)
    # ... execute task ...
```

---

## 📊 Attribute Mapping

| SDD Event | OTEL Span Attribute | Type |
|---|---|---|
| `runtime.session.start` | `sdd.session_id` | string |
| `governance.violation` | `sdd.violation_type` | string |
| Token budget utilization | `sdd.budget_utilization_pct` | number (0–100) |
| Context compression | `sdd.compression_ratio` | number (0–1, where <1 = compressed) |
| Decision source | `sdd.decision_source` | string (canonical \| guide \| heuristic) |

---

## Enforcement Steps

- Verify every agentic operation includes a valid `trace_id` (32 hex chars) and `span_id` (16 hex chars)
- Confirm `traceparent` header follows the format `00-<trace_id>-<span_id>-<flags>`
- Confirm parent span references are correct for non-root operations
- Verify all SDD-specific attributes use the `sdd.*` namespace
- If OTEL export is mandatory and exporter is unreachable, confirm operation is blocked and escalated

---

## 🔗 Related

- [M007: Telemetry](M007_TELEMETRY.md) — Mandatory event emission
- [M008: Audit Integrity](M008_AUDIT_INTEGRITY.md) — Append-only audit trail
- [telemetry/INDEX.md](../telemetry/INDEX.md) — Telemetry architecture overview
- [governance-events.md](../telemetry/governance-events.md) — Event schema with OTEL mapping
