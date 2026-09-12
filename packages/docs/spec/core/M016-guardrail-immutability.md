# M016: Guardrail Non-Regression

## Status

- **Accepted** ✅
- Proposed: 2026-05-20
- Accepted: 2026-05-20
- Review Date: 2026-11-20

---

## Mandate

**Guardrails MAY be incremented and optimized, but MUST NEVER regress — no removal of coverage, no hacks, no code smells.**

| Field | Value |
|-------|-------|
| ID | M016 |
| Type | MANDATE |
| Criticality | high |
| Customizable | No |
| Status | required |

---

## Context

**Problem**:
Guardrails encode safety and governance constraints that protect the integrity of the agentic system. Past incidents showed that:

- Automated refactors silently dropped guardrail checks without failing tests
- New skill implementations replaced existing guardrail logic instead of extending it
- Runtime updates patched guardrail-adjacent code and inadvertently disabled enforcement paths
- "Quick fix" hacks introduced technical debt that gradually eroded guardrail effectiveness
- CI pipelines allowed guardrail regressions to merge because no test explicitly asserted guardrail presence

**Clarification**:
Guardrails are not frozen. Increments (adding new checks, improving performance, refactoring for clarity) are encouraged. The prohibition is on **regression**: any change that reduces coverage, weakens a check, or introduces hacks and code smells.

---

## Decision

**Guardrail changes MUST be net-positive or neutral. Regression is never acceptable.**

### Allowed

- Adding new checks or expanding coverage of an existing check
- Refactoring guardrail internals for clarity, performance, or testability
- Composing new capabilities on top of existing guardrails
- Updating error messages or audit metadata without changing enforcement logic

### Prohibited (Regression)

The following are NEVER permitted without an explicit RFC approved by the human owner:

1. **Removing** a guardrail check or narrowing its scope
2. **Disabling** a guardrail via feature flag, config override, or conditional bypass
3. **Silencing** guardrail errors or suppressing guardrail exceptions
4. **Weakening** a strict check to a warning without equivalent compensating control
5. **Hacks**: bypassing the guardrail path with an ad-hoc workaround
6. **Code smells**: dead branches, commented-out checks, unreachable conditions left in guardrail code
7. **Removing** a guardrail test without replacing it with a stricter equivalent

### Required Behaviors

1. **Composition over replacement**: Extend guardrail behavior; never replace it wholesale.
2. **Audit on modification**: Any change to guardrail code MUST emit a `GovernanceEvent` with `event_type=GUARDRAIL_MODIFIED`.
3. **Test coverage is mandatory**: Every guardrail MUST have at least one test that asserts it blocks the violation it was designed to catch.
4. **CI non-regression gate**: The CI pipeline MUST verify no guardrail surface was reduced relative to the base branch.
5. **Code quality gate**: Guardrail code MUST pass linting (no code smells, no dead code, no hacks).

### Enforcement

- The `SkillEngine` MUST reject any handshake that declares intent to regress a guardrail without an active RFC token.
- The code review guardrail (`test_guardrail_code_review.py`) MUST include a test case for this mandate.
- Violations are logged to `.providence/audit-trail/compliance-events.jsonl` with `severity=critical`.

---

## Rationale

Guardrails are governance infrastructure, not feature code. Incremental improvement is healthy and expected — the system should get safer over time. The danger is the opposite direction: silent regression through hacks, shortcuts, or lazy refactors that reduce enforcement coverage without any visible signal to the human owner.

The asymmetry is the key: a guardrail that got stronger is invisible (no incident). A guardrail that got weaker is invisible too — until a violation slips through.

---

## Consequences

### Positive ✅

- Guardrails can evolve and improve over time
- Regressions are caught at CI, not in production
- Hacks and code smells are blocked at review, not accumulated
- Human owner is informed before any coverage reduction

### Negative ⚠️

- Legitimate coverage reduction (e.g., removing an obsolete check) requires RFC overhead

---

## Related Decisions

- ADR-007: Implementation Guardrails — Design First (guardrails as design contracts)
- ADR-008: Code Review Governance (architect sign-off before merge)
- ADR-012: Handshake Enforcement M015 (SkillEngine blocks unauthorized operations)
- M010: Delivery Hygiene Enforcement (no autonomous git operations)
- M015: Bidirectional Agent Handshake (blocks unauthorized skill execution)

---

## See Also

- `packages/core/providence_core/tests/execution/test_guardrail_code_review.py`
- `.providence/source/mandates/mandates.md`
- `.providence/audit-trail/compliance-events.jsonl`
