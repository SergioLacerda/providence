# Runtime API Integration Guide

This guide documents the practical runtime integration contract for external agent frameworks such as LangGraph, CrewAI, and AutoGen.

## Scope

SDD integrates as a governance layer in front of your orchestration runtime.
It does not replace your framework scheduler, memory, or tool routing.

Use the Providence runtime API/CLI for:

- workspace governance health (AHP + GAP)
- governed context queries
- telemetry and compliance event logging
- drift detection before/after agent execution
- capability-oriented execution via `providence skills run`

## Skill-First Invocation Model

- Agent-facing default: `skills-first`.
- Internal layering: `CLI adapter -> Skill Runtime -> Core/Runtime packages`.
- Governed fallback: `skills -> CLI primitives`.

Canonical flow:

`preflight -> execute -> postcheck -> telemetry`

## Runtime Contract (Stable Surface)

### 1) Health Gate (pre-flight)

```bash
providence runtime status --verbose
```

Expected behavior:

- exit `0`: usable state (`HEALTHY` or acceptable partial state)
- non-zero: block execution and trigger remediation workflow

Purpose:

- verify handshake state (AHP)
- verify governance activation state (GAP)
- detect runtime drift before agent execution

### 2) Governed Context Query (minimal)

```bash
providence ask "<query>"
```

Command contract:

- query text is hashed (not stored raw)
- returns compact governance context answer
- use when you only need a lightweight context fetch

### 3) Governed Context Query (full telemetry)

```bash
providence ask --full "<query>" \
  --tokens-input 150 \
  --tokens-output 60 \
  --log-format jsonl
```

Command contract:

- emits full microtransaction telemetry
- supports explicit token inputs for budget accounting
- writes compliance events to runtime log

Supported options:

- `--log-path`
- `--log-format` (`jsonl` or `compact`)
- `--tokens-input`
- `--tokens-output`

### 4) Bootstrap/Activation Refresh

```bash
providence bootstrap run
```

Use when:

- new workspace/session activation is required
- governance artifacts were refreshed and runtime cache must be synchronized

Optional guard:

- `--session-guard-hours <n>`

### 5) Capability Execution (skills-first)

```bash
providence skills run sdd-validate-governance
```

Contract:

- returns policy-oriented result (`policy_result`, `reason`, `exit_code`)
- emits skill runtime telemetry (`runtime.skill.run`) when telemetry sink is configured
- keeps fallback command references for governed escalation
- always includes `governance_footer` in JSON/text final output:
  `PROVIDENCE GOVERNANCE: drift=<status> | governance=<status> | profile=<profile>`

## Response Footer Contract

Governed outputs must end with a compact governance footer.

- Canonical source: `providence_runtime.format_governance_footer(...)`
- Required format:
  `PROVIDENCE GOVERNANCE: drift=<status> | governance=<status> | profile=<profile>`
- Applies to:
  - `providence skills run`
  - `providence runtime status`
  - governed ask flows (`providence ask`, `providence ask --full`)

## Integration Pattern by Framework

## LangGraph

Recommended insertion points:

1. Pre-graph run hook: call `providence runtime status --verbose`
2. Retrieval/context node: call `providence ask`/`providence ask --full`
3. Post-run hook: record final status and optionally re-check drift

Minimal shell adapter:

```python
import subprocess


def sdd_health_gate() -> None:
    subprocess.run(
        ["sdd", "runtime", "status", "--verbose"],
        check=True,
        capture_output=True,
        text=True,
    )


def sdd_to_otel(event: dict) -> dict:
    from providence_telemetry import to_otel_attributes

    return to_otel_attributes(
        event,
        service_name="langgraph-agent",
        service_version="1.0.0",
    )
```

## CrewAI

Recommended insertion points:

1. Before `Crew.kickoff()`: run health gate
2. In agent tool wrapper: route policy/spec questions to `providence ask --full`
3. For intent-level actions, prefer `providence skills run <skill>`
4. After task completion: persist/ship compliance log artifact

OTel mapping adapter:

```python
from providence_telemetry import to_otel_attributes


def crew_emit_event(event: dict, trace_id: str, span_id: str) -> dict:
    return to_otel_attributes(
        event,
        service_name="crewai-runtime",
        service_version="1.0.0",
        trace_id=trace_id,
        span_id=span_id,
    )
```

## AutoGen

Recommended insertion points:

1. Before starting chat loop: run health gate
2. In custom tool/function bridge: map governance questions to `providence ask` or `providence ask --full`
3. Use `providence skills run` for capability-oriented tasks before low-level command fallback
4. In termination callback: run drift check and archive logs

OTel mapping adapter:

```python
from providence_telemetry import to_otel_attributes


def autogen_event_attrs(event: dict) -> dict:
    # Example event:
    # {"type": "governance.context_load", "severity": "INFO", "tokens_delta": 31}
    return to_otel_attributes(
        event,
        service_name="autogen-orchestrator",
        service_version="1.0.0",
    )
```

## Error Handling and Exit Codes

Treat Providence commands as hard gates for runtime safety:

- `runtime status` non-zero: stop orchestration loop
- budget/compliance failure in `ask --full`: fallback to safe response path
- missing artifacts: run compile/bootstrap remediation before retry

Suggested policy:

1. Fail closed on governance state mismatch.
2. Retry only after explicit remediation step.
3. Never bypass the health gate in production mode.

## Observability

For integration-grade observability, always prefer:

- `ask --full` for audit-critical flows
- explicit token metrics (`--tokens-input`, `--tokens-output`)
- structured log format (`--log-format jsonl`)

Recommended export flow:

1. Keep `.providence/runtime/compliance-events.jsonl` as append-only local audit trail.
2. Forward copies to central SIEM/observability pipeline.
3. Correlate Providence events with framework run/session IDs.

### Direct OTEL Attribute Mapping

Use `providence_telemetry.to_otel_attributes` to normalize runtime events before exporting:

```python
from providence_telemetry import to_otel_attributes

event = {
    "type": "governance.context_load",
    "timestamp": "2026-05-12T14:10:00Z",
    "severity": "WARN",
    "tokens_delta": 42,
    "cache_hit": False,
}

attrs = to_otel_attributes(
    event,
    service_name="my-agent-runtime",
    service_version="2.3.0",
    trace_id="trace-123",
    span_id="span-abc",
)

# attrs now contains:
# - service.name / service.version
# - event.name / event.time / event.domain
# - log.severity / log.severity_number
# - sdd.* namespaced attributes for governance metadata
```

## End-to-End Example (Framework-Agnostic)

```bash
# 1) Validate runtime governance state
providence runtime status --verbose

# 2) Query governed context used by orchestration layer
providence ask --full "What constraints apply to this deployment action?" \
  --tokens-input 220 \
  --tokens-output 80 \
  --log-format jsonl

# 3) Refresh bootstrap state if needed between sessions
providence bootstrap run
```

## Production Checklist

- [ ] `providence runtime status --verbose` executed before every run
- [ ] Context queries routed through `providence ask` or `providence ask --full`
- [ ] Compliance logs persisted and exported
- [ ] Bootstrap refresh policy defined (`session_guard_hours`)
- [ ] Fail-closed behavior documented in the orchestration runtime
