# RFC/ADR Process — Architectural Decision Records

**Status:** Active (2026-05-11)

**Overview:** Defines the lifecycle for proposing, reviewing, and recording architectural decisions in the providence project.

---

## What Is an RFC? What Is an ADR?

| Term | Stage | Purpose |
|------|-------|---------|
| **RFC** (Request for Comments) | Open discussion | Propose a decision, gather feedback, explore alternatives |
| **ADR** (Architectural Decision Record) | Closed record | Capture a decision after it is accepted, as immutable history |

An RFC becomes an ADR when it is **accepted**. RFCs that are rejected are also recorded as ADRs with status `Rejected`.

---

## When to Write an RFC/ADR

Write an RFC when the decision:

- **Affects ≥ 2 packages** (e.g., changing the artifact format impacts compiler + runtime)
- **Is a breaking change** (always requires RFC + BREAKING_CHANGES.md process)
- **Introduces a new external dependency** (security surface, licensing, maintenance burden)
- **Changes a public API or event schema** (downstream consumers must adapt)
- **Overrides an existing ADR** (must reference and supersede it)
- **Requires cross-team coordination** (CLI team + runtime team)

**Skip the RFC** for:

- Single-package internal refactors
- Bug fixes with no behavior change
- Adding optional flags or fields (backward compatible)
- Documentation improvements
- Performance improvements with no API change

In these cases, a `DECISIONS.md` entry in the relevant package is sufficient.

---

## RFC Lifecycle

```
Draft → Open → Accepted → Implemented
                └→ Rejected
                └→ Withdrawn

Implemented → Superseded (by a newer ADR)
```

### Stages

| Stage | Description | Duration |
|-------|-------------|---------|
| **Draft** | Author is writing the RFC, not yet ready for review | No time limit |
| **Open** | RFC is open for community comments | 7 days (standard), 14 days (cross-team/breaking) |
| **Accepted** | Decision made, RFC converted to ADR | Immediate after comment period |
| **Rejected** | Proposal declined; reasons documented | Immediate after comment period |
| **Withdrawn** | Author withdrew before decision | Immediate |
| **Implemented** | Code changes merged; ADR reflects final state | After PR merged |
| **Superseded** | Replaced by a newer ADR | On newer ADR acceptance |

---

## How to Write an RFC

### Step 1 — Copy the Template

```bash
cp docs/spec/decisions/RFC-TEMPLATE.md docs/spec/decisions/RFC-NNN-<slug>.md
# Example: RFC-011-switch-to-orjson.md
```

Use the next available number after the highest existing ADR (currently ADR-010, so next is RFC-011).

### Step 2 — Fill in the Template

Complete all required sections:

- **Context**: What problem are you solving? What is the current state?
- **Proposed Decision**: What are you proposing, in one sentence?
- **Alternatives Considered**: At least 2 alternatives with rejection reasons
- **Consequences**: Positive, negative, and risks
- **Acceptance Criteria**: How will we know this is correctly implemented?

### Step 3 — Open for Review

Submit a Pull Request with the RFC file. Add the label `rfc` to the PR. Tag reviewers:

- Package owner(s) for affected packages
- At least 1 core maintainer

### Step 4 — Comment Period

Standard: **7 days** open for comments.
Cross-team or breaking changes: **14 days**.

All objections must be addressed in the RFC text (update Alternatives or add a Risks section).

### Step 5 — Decision

After the comment period, the core maintainer makes the call:

- **Accept**: Rename file from `RFC-NNN-*` to `ADR-NNN-*`, update status to `Accepted`
- **Reject**: Keep as `ADR-NNN-*`, update status to `Rejected`, document reason
- **Defer**: Extend comment period by 7 days

### Step 6 — Implement

Merge the implementation PR. Update the ADR status from `Accepted` to `Implemented`. Add a reference to the merged PR.

### Step 7 — Supersede (if needed)

If a future decision overrides this one, update the old ADR status to `Superseded by ADR-NNN`.

---

## ADR Format

All ADRs follow this format (consistent with existing ADR-001 through ADR-010):

```markdown
# ADR-NNN: <Title>

## Status
- **<Accepted | Rejected | Implemented | Superseded>** <emoji>
- Proposed: YYYY-MM-DD
- Accepted: YYYY-MM-DD
- Review Date: YYYY-MM-DD (+2 years from acceptance)

---

## Context

**Problem**: <One paragraph describing the problem>

**Scale/Scope**: <What parts of the system are affected?>

---

## Decision

**<Imperative statement of the decision>**

<Explanation paragraph>

---

## Consequences

### Positive ✅
- <Benefit 1>
- <Benefit 2>

### Negative ⚠️
- <Trade-off 1>
- <Trade-off 2>

### Risks 🚨
- <Risk 1 — with mitigation>

---

## Alternatives Considered

### 1. <Alternative name> — **Rejected because**: <reason>

---

## Enforcement Mechanisms

<How this decision is enforced: CI checks, linting rules, review checklists>

---

## Related ADRs

- ADR-NNN: <Related title>
```

---

## Relationship to BREAKING_CHANGES.md

All **breaking changes** require:

1. This RFC process (Steps 1–7 above)
2. Following the steps in [BREAKING_CHANGES.md](BREAKING_CHANGES.md):
   - CHANGELOG entry
   - Deprecation warning in previous minor version
   - Major version bump

Non-breaking architectural changes use only this RFC process.

---

## ADR vs DECISIONS.md

| When to use | Document |
|-------------|---------|
| Cross-package or high-impact decision | ADR in `docs/spec/decisions/` |
| Package-internal implementation choice | Entry in `packages/<pkg>/DECISIONS.md` |
| Incident-driven decision (postmortem) | ADR with `-INCIDENT-` in filename |

---

## Existing ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| `ADR-001` | Clean Architecture 8-Layer Pattern | Implemented ✅ | 2025-06-20 |
| `ADR-002` | Async-First, No Blocking I/O | Implemented ✅ | 2025-06-20 |
| `ADR-003` | Ports & Adapters Pattern | Implemented ✅ | 2025-06-20 |
| `ADR-004` | Vector Index Strategy | Implemented ✅ | 2025-06-20 |
| `ADR-005` | Thread Isolation Mandatory | Implemented ✅ | 2025-06-20 |
| `ADR-006` | Append-Only Storage | Implemented ✅ | 2025-06-20 |
| `ADR-007` | Implementation Guardrails: Design-First | Implemented ✅ | 2025-06-20 |
| `ADR-008` | Code Review Governance | Implemented ✅ | 2025-06-20 |
| `ADR-008-INCIDENT` | Incident Response Process | Implemented ✅ | 2026-04-21 |
| `ADR-009` | Test Location Convention | Implemented ✅ | 2025-06-20 |
| `ADR-010` | Spec-Compiled Artifact Contract | Implemented ✅ | 2025-06-20 |

Next ADR number: **ADR-011**

---

## Quick Reference

```
Need a decision?
├── Affects 1 package only, no API change → DECISIONS.md
├── Affects 2+ packages or public API → RFC → ADR (docs/spec/decisions/)
└── Is a breaking change → RFC + BREAKING_CHANGES.md steps

Copy template: docs/spec/decisions/RFC-TEMPLATE.md
Next ADR number: ADR-011
Review period: 7 days (14 for cross-team/breaking)
Minimum approvals: 1 core maintainer
```
