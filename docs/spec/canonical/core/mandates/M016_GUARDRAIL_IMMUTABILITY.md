# Mandate: Guardrail Non-Regression

**ID:** M016
**Type:** MANDATE
**Enforcement:** HARD
**Required:** true
**Phase:** pre-execution

---

## Objective

Ensure that guardrails evolve in a net-positive direction. Increments and
optimizations are allowed and encouraged. Regression — any change that removes
coverage, weakens enforcement, introduces hacks, or leaves code smells — is
never permitted.

---

## Requirements

1. **Non-regression**: Guardrail changes MUST be net-positive or neutral.
   Any change that reduces enforcement coverage is a violation.

2. **Composition over replacement**: New capabilities MUST extend guardrail
   behavior, never replace it wholesale.

3. **No hacks or code smells**: Guardrail code MUST be clean — no dead
   branches, commented-out checks, ad-hoc bypasses, or unreachable conditions.

4. **Audit on modification**: Any change to guardrail code MUST emit a
   `GovernanceEvent` with `event_type=GUARDRAIL_MODIFIED`.

5. **Mandatory test coverage**: Every guardrail MUST have at least one test
   asserting it blocks its target violation. Removing this test is a blocking
   violation.

6. **CI non-regression gate**: The CI pipeline MUST verify no guardrail
   surface was reduced relative to the base branch.

---

## Allowed vs. Prohibited

**Allowed** (increment / optimize):

- Adding new checks or expanding coverage of an existing check
- Refactoring internals for clarity, performance, or testability
- Updating error messages or audit metadata without changing enforcement logic

**Prohibited** (regression):

- Removing or narrowing a guardrail check
- Disabling via feature flag, config override, or conditional bypass
- Silencing errors or suppressing exceptions
- Weakening a strict check to a warning without a compensating control
- Hacks: ad-hoc workarounds that bypass the guardrail path
- Code smells: dead code, commented-out checks, unused branches in guardrail code
- Removing a guardrail test without a stricter replacement

RFC required from human owner for any prohibited action.

---

## Enforcement

The `SkillEngine` MUST reject handshakes declaring intent to regress a
guardrail without an active RFC token. Violations are logged to
`.providence/audit-trail/compliance-events.jsonl` with `severity=critical`.

---

## Rationale

Guardrails are governance infrastructure. The system should get safer over
time, not weaker. Silent regression through hacks or lazy refactors is
indistinguishable from no regression — until a violation slips through.

---

## Enforcement Steps

- Verify no guardrail check was removed or narrowed in this change set
- Verify new capabilities extend existing guardrail behavior (composition over replacement)
- Confirm guardrail code contains no dead branches, commented-out checks, ad-hoc bypasses, or unreachable conditions
- Confirm a `GovernanceEvent` with `event_type=GUARDRAIL_MODIFIED` was emitted for any guardrail code change
- Confirm every modified guardrail has at least one test asserting it blocks its target violation
- Confirm CI non-regression gate verifies no guardrail surface was reduced relative to the base branch

---

## Related

- ADR-007: Implementation Guardrails — Design First
- ADR-008: Code Review Governance
- ADR-012: Handshake Enforcement M015
- M010: Delivery Hygiene Enforcement
- M015: Bidirectional Agent Handshake
- `docs/spec/core/M016-guardrail-immutability.md` (full design document)
