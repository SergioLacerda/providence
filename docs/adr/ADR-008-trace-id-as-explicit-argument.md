# ADR-008 — `trace_id` Propagation as Explicit Function Argument

**Status:** Accepted
**Date:** 2026-05-21
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

`RuntimeEvent.trace_id` was a mandatory field, but each call site generated its own UUID.
A single `providence ask` invocation produced multiple `RuntimeEvent` entries with unrelated
`trace_id` values, making it impossible to reconstruct a request lifecycle from the
telemetry JSONL sink.

The observability plan required that all events produced within a single CLI command share
one `trace_id`, queryable via `providence telemetry query --trace-id <id>`.

---

## Decision

**`trace_id` travels as an explicit function argument through the call chain. No
thread-locals, no context variables, no globals.**

Flow:

```
CLI entrypoint
  ├─ generate trace_id = uuid4()
  │
  ├─ call runtime entry point(trace_id=trace_id)
  │     └─ emit RuntimeEvent(trace_id=trace_id, ...)  [all events, same id]
  │
  └─ emit governance.compliance.score(trace_id=trace_id)
```

The runtime's public entry points accept `trace_id: str | None = None`. When provided,
it is used for all events in that call. When absent (direct runtime use without CLI),
a new UUID is generated — preserving existing standalone behaviour.

---

## Rationale

- **Thread-locals rejected:** invisible coupling between caller and callee; breaks in
  async contexts and multi-threaded test runners.
- **Global context variable rejected:** same hidden-state problem; makes unit-testing
  propagation behavior difficult.
- **Explicit argument accepted:** the propagation path is visible in signatures, testable
  in isolation, and works correctly in both sync and async call stacks.

---

## Consequences

- Runtime entry points that previously took no `trace_id` parameter gain an optional one;
  callers that do not pass it retain their existing behaviour.
- Integration tests must assert that all `RuntimeEvent` entries from a single CLI call
  share one `trace_id` and that two sequential calls produce distinct ids.
- New runtime entry points must include `trace_id: str | None = None` in their signature
  from day one.

---

## Links

- Implementation: `packages/core/providence_runtime/`, `packages/interfaces/providence_cli/`
- Related: ADR-001 (Runtime Authority Boundary), M007 (Telemetry Enforcement)
