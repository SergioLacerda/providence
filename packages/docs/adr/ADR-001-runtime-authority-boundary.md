# ADR-001 — Runtime Authority Boundary

**Status:** Accepted
**Date:** 2026-05-10
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

The introduction of `providence_runtime` creates a second active layer in the governance
stack alongside `sdd_compiler`.  Both layers process governance artifacts, which
raises the risk of a dual source of truth: compiler defines semantics, runtime
redefines or re-interprets them at execution time.

The improvement plan (§12 — Compiler–Runtime Boundary Contract) requires that
this boundary be made explicit and enforced by a formal architectural rule.

---

## Decision

**`providence_runtime` is a pure execution engine.  It is not a normative authority.**

The canonical decision chain is immutable:

```
docs/spec/canonical/  →  sdd_compiler  →  compiled artifacts  →  providence_runtime  →  CLI/IDE
(normative source)       (semantic        (versioned DTOs)       (executor)
                          authority)
```

Any change that alters governance *meaning* must originate in
`docs/spec/canonical/`, be compiled through `sdd_compiler`, and produce a new
versioned artifact.  Runtime code that infers, extends, or overrides normative
semantics from any other source is a violation of this boundary.

---

## Consequences

### Permitted in `providence_runtime`

- Loading and consuming compiled artifacts (read-only).
- Executing policy checks against artifact state.
- Managing session lifecycle and drift detection.
- Emitting structured telemetry events.
- Returning deterministic outcomes for fixed `(profile, artifact, session)` tuples.

### Prohibited in `providence_runtime`

- Parsing `docs/spec/canonical/` or any source markdown for enforcement logic.
- Introducing policy semantics not present in compiled artifacts.
- Computing fingerprints with a non-canonical algorithm.
- Reusing session cache across artifact fingerprint mismatches.
- Emitting events without `event_schema_version`, `trace_id`, or `ts`.

---

## Enforcement Mechanisms

| Gate | Mechanism | Location |
|---|---|---|
| No New Rules | Code review policy: runtime PRs must not introduce normative semantics | ADR + CLAUDE.md |
| Traceability | `TraceabilityValidator.validate_event()` on sensitive events | `providence_runtime.validator` |
| Compatibility | `SchemaValidator.validate_artifact()` before any artifact is consumed | `providence_runtime.validator` |
| Determinism | Replay harness in `tests/test_determinism.py` (20 iterations) | CI test suite |
| Audit | `RuntimeEvent.event_schema_version` mandatory; passive JSONL sink | `providence_runtime.telemetry` |

---

## Failure Semantics

When the boundary is violated at runtime:

- **Sensitive path violations** → fail closed (`PolicyResult.allowed = False`, severity `hard`).
- **Non-sensitive path violations** → soft warning with deterministic `remediation` command.
- **Corrupt/missing artifact** → `PolicyEngine.evaluate(has_artifact=False, is_sensitive=True)` → blocked.

---

## Review Trigger

This ADR must be revisited if:

1. `providence_runtime` is proposed to accept raw spec documents as input.
2. A new fingerprint algorithm is introduced.
3. Session schema is extended with new semantics beyond the mandatory fields in §12.3.
4. Runtime policy adapter versions diverge from compiler output versions.
