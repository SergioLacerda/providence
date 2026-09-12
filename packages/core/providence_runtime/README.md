# providence_runtime — Core Telemetry and Runtime Management

**Module:** `packages/core/providence_runtime`
**Version:** 3.0
**Status:** Production-Ready (Phases 0-2)

---

## Overview

`providence_runtime` is the foundation for compliance audit trails, runtime event capture, token economy metrics, and alert webhooks in the SDD framework. It provides zero-dependency telemetry export with optional OTLP bridge integration and Prometheus metrics exposition.

### Key Components

| Component | Purpose | File |
|-----------|---------|------|
| **Compliance Audit Trail** | Event-based compliance logging with agent tracking, schema validation, and log rotation | `governance/compliance.py` |
| **TelemetrySink** | Central event emission and persistence to JSONL | `telemetry.py` |
| **TelemetryReader** | Ad-hoc query interface over JSONL event logs | `reader.py` |
| **TokenEconomyCollector** | Thread-safe aggregation of token consumption metrics | `metrics.py` |
| **AlertDispatcher** | Event-triggered webhook dispatch (PagerDuty, Slack, generic) | `alerts.py` |
| **OtelBridge** | Optional OTLP HTTP exporter (zero-overhead if unset) | `otel.py` |

---

## Configuration

All `providence_runtime` behavior is controlled via environment variables. Default values enable zero-overhead operation with opt-in features.

### Compliance & Audit Trail

| Env Var | Default | Purpose | Example |
|---------|---------|---------|---------|
| `SDD_AGENT_ID` | (unset) | Identifier for the agent/service emitting events. Recorded in compliance audit trail. | `"agent-compile-v2"`, `"agent-governance"` |

**Location:** Events written to `.providence/runtime/compliance-events.jsonl`

```bash
# Enable agent tracking
export SDD_AGENT_ID="my-agent-name"
providence ask "some query"
# Event now includes: "agent_id": "my-agent-name"
```

---

### Prometheus Metrics

| Env Var | Default | Purpose | Example |
|---------|---------|---------|---------|
| `SDD_METRICS_PORT` | `9090` | Port for Prometheus `/metrics` HTTP endpoint when running `sdd metrics serve` | `9090`, `8888` |

**Usage:**
```bash
# Start metrics server
sdd metrics serve --port 9090

# In another terminal
curl http://localhost:9090/metrics | head -20

# Or with custom port
SDD_METRICS_PORT=8888 sdd metrics serve
```

**Metrics Exposed:**
- `sdd_tokens_input_total`, `sdd_tokens_output_total`, `sdd_tokens_total_total` (counters)
- `sdd_cost_usd_total` (counter, USD)
- `sdd_llm_calls_total` (counter)
- `sdd_budget_utilization_pct` (gauge, 0-100)
- `sdd_budget_warn_total`, `sdd_budget_breach_total`, `sdd_retry_cap_total` (counters)
- Per-model variants: `sdd_tokens_by_model_{input,output,total}_total{model="..."}`, `sdd_cost_usd_by_model_total{model="..."}`

**Format:** Prometheus text format (version 0.0.4), compatible with Grafana, Prometheus, and other scrape-based collectors.

---

### Alert Webhooks

Event-triggered webhook dispatch for budget breaches and retry ceiling hits. Supports PagerDuty Events API v2, Slack incoming hooks, and generic JSON.

| Env Var | Default | Purpose | Example |
|---------|---------|---------|---------|
| `SDD_WEBHOOK_URL` | (unset) | Webhook destination URL. If unset, alert dispatch is **disabled** (zero overhead). | `https://events.pagerduty.com/v2/enqueue`, `https://hooks.slack.com/services/...` |
| `SDD_WEBHOOK_TYPE` | `generic` | Payload format: `pagerduty`, `slack`, or `generic` | `pagerduty`, `slack` |
| `SDD_WEBHOOK_EVENTS` | `economy.budget.breach,economy.budget.breach.tokens,economy.budget.breach.usd,economy.retry.cap.reached` | Comma-separated event types that trigger webhook dispatch | `economy.budget.breach`, custom list |
| `SDD_WEBHOOK_TIMEOUT` | `5` | HTTP socket timeout in seconds | `10`, `30` |
| `SDD_PD_ROUTING_KEY` | (unset) | PagerDuty Events API v2 routing key (required if `webhook_type=pagerduty`) | Your PagerDuty integration routing key |

**Setup Examples:**

**PagerDuty:**
```bash
export SDD_WEBHOOK_URL="https://events.pagerduty.com/v2/enqueue"
export SDD_WEBHOOK_TYPE="pagerduty"
export SDD_PD_ROUTING_KEY="YOUR_ROUTING_KEY"

providence ask "query"  # Will POST to PagerDuty on budget breach
```

**Slack:**
```bash
export SDD_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export SDD_WEBHOOK_TYPE="slack"

providence ask "query"  # Will POST to Slack with formatted message
```

**Generic JSON:**
```bash
export SDD_WEBHOOK_URL="http://localhost:9999/alerts"
export SDD_WEBHOOK_TYPE="generic"

providence ask "query"  # Will POST event JSON to your endpoint
```

**Behavior:**
- Dispatch is **best-effort** and **non-blocking** — webhook errors do not interrupt the agent
- Only events in `SDD_WEBHOOK_EVENTS` trigger dispatch
- Default events: budget breach (all variants) and retry ceiling breaches
- Payload includes full `RuntimeEvent` fields (trace_id, span_id, workspace_id, agent_id, details, etc.)

---

### OpenTelemetry (OTLP) Export

Optional OTLP HTTP span export. If unset, **zero overhead** (OtelBridge not instantiated).

| Env Var | Default | Purpose | Example |
|---------|---------|---------|---------|
| `SDD_OTEL_EXPORTER_ENDPOINT` | (unset) | Canonical OTLP HTTP collector endpoint. If unset (and the legacy alias below is also unset), OTLP export disabled. | `http://localhost:4318`, `https://otel.example.com` |
| `SDD_OTEL_ENDPOINT` | (unset) | **Deprecated alias** for `SDD_OTEL_EXPORTER_ENDPOINT`, kept for backward compatibility with existing CLI configs. Emits a `DeprecationWarning`-level log line when used. If both are set, `SDD_OTEL_EXPORTER_ENDPOINT` wins. | — |
| `SDD_OTEL_API_KEY` | (unset) | Optional API key header (`DD-API-KEY` for Datadog hosts, `Authorization: Bearer` otherwise). | — |
| `SDD_OTEL_ALLOW_INSECURE_HTTP` | (unset) | Allow plaintext `http://` export to non-local hosts (local/loopback is always allowed). | `1` |

All consumers (runtime `create_sink()`, CLI `ask` telemetry) resolve the endpoint through the single `providence_runtime.telemetry.get_otel_endpoint()` helper, so both layers apply the same precedence instead of reading the environment independently.

**Setup:**
```bash
# Send traces to local OTEL collector
export SDD_OTEL_EXPORTER_ENDPOINT="http://localhost:4318"

providence ask "query"  # Spans exported to OTEL collector
```

**Behavior:**
- Spans exported after event emit (non-blocking)
- Includes trace_id and span_id for correlation
- Compatible with Jaeger, Datadog, GCP Cloud Trace, etc.

**Sampling & retention policy:**
- **No sampling.** Every emitted `RuntimeEvent` is exported when OTLP is enabled — there is no probabilistic or rate-based sampler in this exporter (`OtlpHttpExporter` is a stdlib-only HTTP client, not backed by `opentelemetry-sdk`). To control export volume, disable OTLP for noisy environments by leaving `SDD_OTEL_EXPORTER_ENDPOINT` unset, or filter/sample at the collector.
- **Retention is the OTLP backend's responsibility.** This project does not manage OTLP-side retention; export is best-effort and non-blocking. The **JSONL sink is the source of truth and local retention boundary** — see `.providence/runtime/compliance-events.jsonl` and the audit-integrity mandate for local log lifecycle. If the OTLP export fails, the JSONL record is unaffected.

---

## API Reference

### TelemetrySink (Event Emission)

Central sink for runtime events. Events are written to JSONL and optionally exported via OTel / webhooks.

```python
from providence_runtime import create_sink, RuntimeEvent

# Create sink (uses env vars for configuration)
sink = create_sink()

# Emit event
event = RuntimeEvent(
    event="governance.ask",
    command="ask",
    status="ok",
    trace_id="trace-123",
    workspace_id="ws-dev",
    agent_id="agent-v1",
    artifact_fingerprint="fp-abc",
    decision_source_refs=["sdd-governance-context"],
    details={"items_matched": 5},
)

sink.emit(event)
# Writes to .providence/runtime/compliance-events.jsonl
# Optionally posts webhook to SDD_WEBHOOK_URL
# Optionally exports span to SDD_OTEL_EXPORTER_ENDPOINT
```

### TelemetryReader (Queries)

Query JSONL event logs for analysis.

```python
from providence_runtime.reader import TelemetryReader
from pathlib import Path

reader = TelemetryReader(Path(".providence/runtime/compliance-events.jsonl"))

# Query by type
events = reader.get_events_by_type("governance.ask", last_hours=24)

# Token statistics
stats = reader.get_token_stats(last_hours=24)
print(f"Total tokens: {stats.total_tokens}")
print(f"Cost: ${stats.cost_usd:.4f}")
print(f"Models: {stats.unique_models}")

# Error analysis
errors = reader.get_error_rate(last_hours=24)
print(f"Error rate: {errors['error_rate']}%")

# Budget status
budget = reader.get_budget_status()
print(f"Budget utilization: {budget.utilization_pct:.1f}%")

# Filter by agent, status, or get latest N events
agent_events = reader.get_events_by_agent("agent-v1")
failures = reader.get_events_by_status("fail")
recent = reader.get_latest_events(50)
```

### TokenEconomyCollector (Metrics Aggregation)

Thread-safe accumulator for token economy metrics.

```python
from providence_runtime.metrics import TokenEconomyCollector, PrometheusTextRenderer
from providence_runtime.reader import TelemetryReader
from pathlib import Path

# Build collector from JSONL replay
reader = TelemetryReader(Path(".providence/runtime/compliance-events.jsonl"))
collector = TokenEconomyCollector.from_reader(reader)
snapshot = collector.snapshot()

print(f"Total tokens: {snapshot.total_tokens_total}")
print(f"Total cost: ${snapshot.total_cost_usd:.4f}")
print(f"Budget utilization: {snapshot.budget_utilization_pct:.1f}%")
print(f"Per-model breakdown: {snapshot.per_model}")

# Render as Prometheus text format
renderer = PrometheusTextRenderer()
prometheus_text = renderer.render(snapshot)
print(prometheus_text)
```

### AlertDispatcher (Webhooks)

Event-triggered webhook dispatch.

```python
from providence_runtime.alerts import AlertDispatcher

# From environment
dispatcher = AlertDispatcher.from_env()  # None if SDD_WEBHOOK_URL unset

if dispatcher:
    event = RuntimeEvent(event="economy.budget.breach", ...)
    dispatcher.on_event(event)  # POST to webhook (best-effort)

# Or explicit construction
dispatcher = AlertDispatcher(
    url="https://hooks.slack.com/services/...",
    webhook_type="slack",
    events=frozenset(["economy.budget.breach"]),
    timeout=10
)
dispatcher.on_event(event)
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────┐
│  Agent Code (providence ask, providence governance, etc.)         │
└──────────────────┬──────────────────────────────────┘
                   │ emit(RuntimeEvent)
                   ▼
       ┌───────────────────────────┐
       │  TelemetrySink.emit()      │
       └────┬──────────────────┬────┘
            │                  │
      Write JSONL        Best-Effort Side-Cars
            │                  │
    .providence/runtime/         ┌─────┴─────┐
    compliance-          │           │
    events.jsonl    AlertDispatcher OtelBridge
            │      (if SDD_WEBHOOK_) (if SDD_OTEL_)
            ▼             │            │
         ┌──────────┐     ▼            ▼
         │ JSONL    │  PagerDuty     OTLP Collector
         │ Archive  │  Slack         (Jaeger, DD, etc)
         │          │  Generic JSON
         └─────┬────┘     │            │
               │          │            │
               ▼          ▼            ▼
         TelemetryReader CLI         Observability
         (sdd metrics)  Dashboard    Platform
         (API queries)  (Future)
```

---

## Event Types

**Fase 0 & 1 Events:**
- `runtime.session.start` — workspace session initialized
- `runtime.drift.detected` — artifact fingerprint mismatch detected
- `policy.validation.pass`, `policy.validation.fail` — governance policy decisions
- `governance.ask` — lightweight compliance query
- `governance.ask.full` — full compliance query (with telemetry)
- `governance.compile.complete` — artifact compilation finished

**Fase 2 Events:**
- `economy.token.consume` — token consumption recorded
- `economy.budget.warn` — budget utilization warning (>90%)
- `economy.budget.breach` — budget utilization breach (≥100%)
- `economy.retry.cap.reached` — retry ceiling exceeded

---

## Event JSON Schema

Each line in `.providence/runtime/compliance-events.jsonl` is a JSON object:

```json
{
  "workspace_id": "ws-dev",
  "agent_id": "agent-compile-v2",
  "work_item_id": "task-123",
  "artifact_fingerprint": "fp-abc123...",
  "schema_version": "3.0",
  "decision_source_refs": ["ADR-001-authority", "sdd-governance-context"],
  "timestamp": "2026-05-15T14:32:00Z",
  "trace_id": "trace-abc123",
  "span_id": "span-abc123",
  "event": "governance.ask",
  "command": "ask",
  "status": "ok",
  "tokens_input": 1250,
  "tokens_output": 350,
  "tokens_total": 1600,
  "budget_utilization_pct": 62.5,
  "details": {
    "items_matched": 5,
    "model": "claude-opus-4-6",
    "cost_usd": 0.0234
  }
}
```

---

## CLI Commands

### sdd metrics summary

Print token economy snapshot to rich table.

```bash
# Print summary
sdd metrics summary

# Filter to last 24 hours
sdd metrics summary --last-hours 24

# Custom JSONL path
sdd metrics summary --jsonl /path/to/events.jsonl
```

**Output:**
```
Token Economy Summary
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━┓
┃ Model     ┃ Input Tokens  ┃ Output Tokens┃ Total      ┃ Est. Cost ┃Call┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━┩
│ claude-op │ 12,450        │ 3,200        │ 15,650     │ $0.1234   │ 47 │
├───────────┼───────────────┼──────────────┼────────────┼───────────┼────┤
│ TOTAL     │ 12,450        │ 3,200        │ 15,650     │ $0.1234   │ 47 │
└───────────┴───────────────┴──────────────┴────────────┴───────────┴────┘

Budget utilization: 62.5% 🟢 OK
Event summary: 0 warns | 1 breaches | 0 retry caps
```

### sdd metrics serve

Start Prometheus `/metrics` endpoint (foreground daemon).

```bash
# Default port 9090
sdd metrics serve

# Custom port
sdd metrics serve --port 8888

# Custom JSONL path
sdd metrics serve --jsonl /path/to/events.jsonl

# Custom refresh interval (seconds)
sdd metrics serve --refresh 60
```

**Behavior:**
- Starts HTTP server on `0.0.0.0:<port>`
- Responds to `GET /metrics` with Prometheus text format
- Background thread reloads JSONL every N seconds
- Press Ctrl+C to stop

**Scrape in Prometheus:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'sdd'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 30s
```

---

## Best Practices

### 1. Always Set `SDD_AGENT_ID`

```bash
export SDD_AGENT_ID="agent-$(hostname)-$(date +%s)"
providence ask "query"
# Now audit trail identifies the agent
```

### 2. Configure Webhooks for Production

```bash
# PagerDuty alerts on budget breach
export SDD_WEBHOOK_URL="https://events.pagerduty.com/v2/enqueue"
export SDD_WEBHOOK_TYPE="pagerduty"
export SDD_PD_ROUTING_KEY="YOUR_KEY"

# Or Slack for team notifications
export SDD_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK"
export SDD_WEBHOOK_TYPE="slack"
```

### 3. Monitor Metrics Periodically

```bash
# Start Prometheus endpoint for long-lived processes
sdd metrics serve &

# In production, configure Prometheus to scrape it
```

### 4. Query Logs for Debugging

```bash
# Analyze error rate
providence ask "query" && python3 -c "
from providence_runtime.reader import TelemetryReader
from pathlib import Path
reader = TelemetryReader(Path('.providence/runtime/compliance-events.jsonl'))
errors = reader.get_error_rate(last_hours=1)
print(f'Error rate: {errors[\"error_rate\"]}%')
"
```

---

## Troubleshooting

### No events in `.providence/runtime/compliance-events.jsonl`

**Check:**
1. Ensure `create_sink()` is called before emitting events
2. Verify `.providence/runtime/` directory exists and is writable
3. Check environment: `echo $SDD_AGENT_ID`

### Webhooks not firing

**Check:**
1. `SDD_WEBHOOK_URL` is set and accessible
2. Event type is in `SDD_WEBHOOK_EVENTS` (default: breach + retry events)
3. No network errors (check firewall, DNS, SSL)
4. Webhook endpoint responding with 2xx status

### Prometheus endpoint not responding

**Check:**
1. Port is available: `lsof -i :9090`
2. Process running: `ps aux | grep "sdd metrics serve"`
3. JSONL file readable: `ls -la .providence/runtime/compliance-events.jsonl`

---

## References

- [Release Notes](../../docs/superpowers/specs/)
- [DECISIONS.md](./DECISIONS.md) — Architecture decisions for providence_runtime
- [Incident Playbooks](../../docs/incidents/PLAYBOOKS.md) — Operational runbooks
