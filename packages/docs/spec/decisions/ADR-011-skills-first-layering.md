# ADR-011: Skills-First Layering

- Status: Accepted
- Date: 2026-05-13

## Context

The project introduced capability-oriented commands (`providence skills ...`) and awakening seeds.
Without a strict boundary, capability execution can leak into CLI command modules,
causing policy drift and coupling.

## Decision

Adopt this layering model:

1. Agent-facing behavior: skills-first.
2. Internal architecture: `CLI adapter -> Skill Runtime -> Core/Runtime packages`.
3. Governed fallback: `skills -> CLI primitives`.

`SkillEngine` in `providence_runtime` is the canonical execution authority for capabilities.
`providence_cli` remains an adapter for input/output and structured response rendering.

## Consequences

- Positive:
  - Single enforcement path for policy/budget/escalation/telemetry.
  - Better reuse from CLI, wizard bootstrap contracts, and external frameworks.
  - Lower coupling and clearer ownership.
- Negative:
  - Requires migration of any residual command-level domain logic.

## Implementation Notes

- Awakening seed contracts are produced by wizard and validated/consumed in runtime.
- Core governance modules observe runtime state, not CLI internals.
