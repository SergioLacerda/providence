# SDD Telemetry — Decision Log

**Module:** `packages/core/providence_telemetry`
**Purpose:** Event logging, token economy tracking, observability
**Owner:** @SergioLacerda

---

## DEC-2026-001: JSONL Format for Event Logs (2026-03-01)

**Decision:** Store events as newline-delimited JSON (JSONL), one event per line

**Rationale:**
- Simple: Each line is independent, no nested structure
- Streamable: Can read/append incrementally
- Observable: grep/jq work naturally
- No schema lock-in: Add fields without breaking old events
- Queryable: Stream processing, filter by timestamp/type

**Example:**
```jsonl
{"timestamp": "2026-05-11T10:00:00Z", "type": "context_load", "query": "mandate", "tokens": 5}
{"timestamp": "2026-05-11T10:00:01Z", "type": "budget_update", "delta": -5, "utilization_pct": 45.0}
```

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** TelemetryEngine in engine.py

---

## DEC-2026-002: Token Economy Tracking (Phase 3 Integration) (2026-02-15)

**Decision:** Emit tokens_delta for every event, sum to compute utilization_pct

**Rationale:**
- Governance: User-visible consumption (not hidden costs)
- Accountability: Each action has explicit cost
- Budgeting: Running total shows remaining allocation
- Recovery: Can replay session to debug usage

**Event field:** tokens_delta (positive = consume, negative = refund)
**Example:** context_load with 10KB of results → tokens_delta: 100 (cost per KB = 10)

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** Phase 3 Token Economy

---

## DEC-2026-003: Event Types (Extensible Set) (2026-03-10)

**Decision:** Define core event types (context_load, budget_update, cache_hit, etc.), extensible

**Rationale:**
- Consistency: All events have type field
- Filtering: Query by type (e.g., all cache_hit events)
- Versioning: Can rename/deprecate types without breaking consumers
- Flexibility: New components can define new types

**Core types:**
- `governance.context_load`: Query context, tokens consumed
- `governance.cache_hit`: Cache returned result
- `economy.budget_update`: Tokens remaining after operation
- `economy.breach`: Budget ≥100% (critical alert)
- `runtime.error`: Caught exception, error type/message
- `compiler.compile_start/end`: Compilation phases and timing

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-004: Timestamp as ISO 8601 UTC (2026-03-15)

**Decision:** All events use ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ) in UTC

**Rationale:**
- Standard: ISO 8601 is universal, no timezone confusion
- Sortable: Lexicographic ordering = chronological
- Parseable: Python datetime.fromisoformat(), no custom parsing
- Observable: grep/sort work naturally on strings

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-005: Structured Metadata (Not Nested Blobs) (2026-03-20)

**Decision:** Each event has flat fields (no nested objects), use prefixes for grouping

**Rationale:**
- Query: jq can filter by top-level fields
- Simple: No nested traversal
- Schema-less: Easy to add fields without versioning

**Example:**
```jsonl
{
  "timestamp": "...",
  "type": "context_load",
  "query": "mandate",
  "matched_count": 15,
  "truncated": false,
  "bytes_loaded": 1024,
  "tokens_delta": 10,
  "cache_hit": false,
  "latency_ms": 2.5
}
```

NOT:
```jsonl
{
  "timestamp": "...",
  "event": {
    "type": "context_load",
    "context": {"query": "mandate", "matched": 15},
    "tokens": {"delta": 10},
    "cache": {"hit": false}
  }
}
```

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-006: File-Based Buffering (No Network) (2026-04-01)

**Decision:** Write events to local .providence/runtime/telemetry.jsonl, not remote server

**Rationale:**
- Simplicity: No network, auth, TLS complexity
- Privacy: Data stays local (user/org can decide export)
- Reliability: No network timeouts blocking application
- Batch export: Can upload to analytics platform later (Phase 6)

**Consequence:** Telemetry log only accessible on local machine (for now)

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-007: Rotating Log Files by Size (2026-04-10)

**Decision:** If telemetry.jsonl exceeds 10MB, rotate to telemetry-YYYY-MM-DD.jsonl

**Rationale:**
- Manageability: Don't accumulate unbounded file
- Archival: Old logs date-stamped for easy cleanup
- Performance: Smaller files = faster grep/analytics
- Disk space: User can delete old logs if needed

**Policy:** Keep last 30 days, auto-delete older files

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-008: No PII (Personally Identifiable Info) in Events (2026-04-15)

**Decision:** Never log: usernames, email addresses, file contents, query results

**Rationale:**
- Privacy: User data stays private
- Compliance: GDPR/CCPA safe (no personal data)
- Security: No credentials/tokens logged
- Trust: User confidence in data handling

**What's OK:**
- Query type (e.g., "context_load")
- Metric values (e.g., bytes_loaded)
- Event counts (e.g., mandates_compiled)

**What's NOT OK:**
- Full query text (redact to hash)
- Command output
- File paths (use relative paths only)

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-009: Telemetry Compression (Intent: Phase 3) (2026-03-01)

**Decision:** Token cost for telemetry itself = 0 (free to emit events)

**Rationale:**
- Fairness: Observability shouldn't consume budget
- Transparency: User can enable detailed logs without "costing" more
- Guidance: Encourages comprehensive instrumentation

**Future:** May change if telemetry becomes heavy (Phase 5.5+)

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-010: Event Immutability (No Retroactive Edits) (2026-05-01)

**Decision:** Events are write-once, never edited after creation

**Rationale:**
- Audit trail: History is immutable, can't be "corrected" retroactively
- Integrity: Rely on event logs for compliance/disputes
- Simplicity: No update/delete logic in telemetry engine

**Consequence:** If you record wrong data, emit a new event to correct (e.g., "cache_hit: false" then "cache_hit_corrected: true")

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-011: OpenTelemetry Semantic Alignment (2026-05-12)

**Decision:** Provide a standard adapter from SDD runtime events to OpenTelemetry-compatible attributes using:

- common OTel service fields (`service.name`, `service.version`)
- event/log fields (`event.name`, `event.time`, `log.severity`, `log.severity_number`)
- SDD namespace fields (`sdd.*`) for governance metadata

**Rationale:**
- Interoperability with observability backends without losing SDD semantics
- Stable contract for integrations (LangGraph, CrewAI, AutoGen, custom runtimes)
- Explicit severity normalization and timestamp guarantees

**Implementation:**
- `providence_telemetry.otel.to_otel_attributes(...)`
- Scalar-safe conversion for attribute payloads
- Optional trace context propagation (`trace_id`, `span_id`)

**Status:** ACTIVE
**Owner:** @SergioLacerda

---
