---
applyTo: "**/*.go"
---

# Testing

Ruleset version: `{{ standalone_ruleset_version }}`
Last verified: `{{ last_verified }}`

Functions kept small and testable in isolation, per `architecture.instructions.md`,
are what makes the Red-Green-Refactor cycle below practical.

## Red-Green-Refactor

All code changes follow this cycle:

1. **Red** â€” write a failing test for the new requirement.
2. **Green** â€” write the minimal implementation to pass the test.
3. **Refactor** â€” clean up the implementation while keeping the test green.

This ensures you're solving the right problem, and that the solution is testable by design.

## Validation

- Test coverage should meet the project's defined threshold.
- Version-control history should show test files created or modified before or alongside implementation files.
- The full test suite passes before you consider a change done.

## Go Projects

- `go test ./...` is green for the changed scope before delivery.
- New behavior is introduced with test-first evidence (a test added or updated before the final implementation state).
- Table-driven tests are used for multi-scenario business rules where appropriate.
- Boundary contracts (ports/interfaces) have focused unit tests without external side effects.
- Race-sensitive changes run under `go test -race` when available.
