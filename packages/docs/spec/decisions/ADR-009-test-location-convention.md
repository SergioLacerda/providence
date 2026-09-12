# ADR-009: Test Location Convention

## Status

- **Accepted** ✅
- Proposed: 2026-05-05
- Accepted: 2026-05-05
- Review Date: 2026-11-05

---

## Context

The repository has two locations where pytest discovers tests:

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests", "tests/contract", "packages"]
```

This dual-root configuration was inherited from the early monorepo structure where
package-level smoke tests lived alongside source code. Without a documented convention,
new contributors place unit tests in inconsistent locations, increasing maintenance
overhead and reducing discoverability.

**Observed pattern:** All current tests under `packages/` are structural (import
verification), not domain logic tests. Domain logic tests live under `tests/`.

---

## Decision

### Rule: test location is determined by test type

| Type | Location | Rationale |
|------|----------|-----------|
| Unit tests | `tests/unit/<package>/` | Central, easy to find, mirrors package name |
| Integration tests | `tests/integration/<domain>/` | Domain-grouped, can span multiple packages |
| Contract tests | `tests/contract/` | Separate because they own golden fixtures |
| E2E tests | `tests/e2e/` (future) | Separate because they require external deps |
| Package smoke tests | `packages/<pkg>/tests/` | Minimal import-level checks only; marked `@pytest.mark.smoke` |

### Prohibited

- Domain logic tests (`assert business_rule(x) == y`) inside `packages/`
- Unit tests for package A placed under `tests/unit/<package-B>/`
- Unmarked tests inside `tests/unit/` or `tests/integration/` (must carry `@pytest.mark.unit` or `@pytest.mark.integration`)

### `make test` scope

`make test` runs `-m "unit or integration"` — this explicitly excludes `contract`,
`e2e`, and `smoke` from the default development loop. Contract tests run in CI via
`make check` (which calls `pytest tests packages` without a `-m` filter).

---

## Consequences

**Positive:**

- Single lookup rule: "where is the test for `providence_core.governance.handshake`?"
  → `tests/unit/governance/`
- `packages/` can be scanned for smoke tests without noise from domain logic
- New test categories (e2e, performance) have a clear home

**Negative:**

- Existing tests in `packages/` that are not smoke tests need to be migrated
  (low priority; none found as of 2026-05-05)

---

## References

- `pyproject.toml` — `[tool.pytest.ini_options]` testpaths and markers
- `Makefile` — `make test` target with `-m "unit or integration"`
- `tests/contract/` — golden-file contract tests (B2, Sprint 5)
- sdd_criticas.md CAT-B item B3
