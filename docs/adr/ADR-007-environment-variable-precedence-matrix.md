# ADR-007 — Environment Variable Precedence Matrix

**Status:** Accepted
**Date:** 2026-05-21
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

Path resolution across `providence_core`, `providence_runtime`, `providence_cli`, and `sdd_compiler` was
ad-hoc: each module resolved workspace root, telemetry sinks, and keyring paths
independently, with different fallback strategies and no shared contract. This caused
tests to accidentally write to the real `.providence/` tree, CI results to differ from local
runs, and integration tests to interfere with each other.

---

## Decision

**A single, explicit precedence matrix governs all path-resolution env vars.**

### Variable classification per environment

| Variable | test | runtime | dev/prod |
|---|---|---|---|
| `SDD_WORKSPACE_ROOT` | O | O | O |
| `SDD_TEST_OUTPUT_DIR` | **R** | **F** | **F** |
| `SDD_COMPLIANCE_EVENTS_PATH` | O | O | O |
| `SDD_TELEMETRY_PATH` | O | O | O |
| `SDD_TRUSTED_KEYRING` | **F** | O | O |
| `SDD_ALLOW_REPO_SDD_MUTATION` | O | **F** | **F** |
| `SDD_SIGNATURE_MODE` | O | O | O |
| `SDD_RUNTIME_ENV` | O | O | O |
| `SDD_GOVERNANCE_MODE` | **F** | O | O |

R = required · O = optional · F = forbidden (fail-fast if present)

### Workspace root precedence

1. `SDD_WORKSPACE_ROOT` (if set and valid)
2. Authority utility `resolve_workspace_root()` / `detect_repo_root()`
3. Safe fallback by context: in `test` → fail with explicit error (no mutable root invented);
   in `runtime`/`dev` → fail-closed or safe-mode per active governance.

### Telemetry/compliance path precedence

- `SDD_COMPLIANCE_EVENTS_PATH` → context default (`<workspace>/.providence/runtime/compliance-events.jsonl`) → in test: redirect to `SDD_TEST_OUTPUT_DIR`
- `SDD_TELEMETRY_PATH` → workspace default path

### Trusted keyring precedence

1. Canonical path `<workspace>/.providence/trust/trusted-keys.json`
2. `SDD_TRUSTED_KEYRING` (non-strict fallback only)
3. In strict mode: absence of canonical path blocks.

### Enforcement

- A variable classified **F** in the active context must fail fast with a diagnostic message.
- A variable classified **R** that is missing must cause an explicit failure or a controlled
  fallback documented in this ADR.
- Every resolution rule has an associated automated check in the contract test suite.

---

## Rationale

- **Per-module ad-hoc resolution rejected:** produces silent cross-test contamination and
  non-reproducible CI behaviour.
- **Single contract accepted:** predictable, testable, and auditable — any deviation is
  caught by the contract suite.

---

## Consequences

- Test fixtures must set `SDD_TEST_OUTPUT_DIR` and unset `SDD_GOVERNANCE_MODE` and
  `SDD_TRUSTED_KEYRING`; fixtures that do not comply fail.
- Adding a new path-resolution variable requires updating this ADR and the matrix validation
  rules before the variable may be used.
- The restriction that `SDD_TEST_OUTPUT_DIR` is **F** in runtime prevents test-only overrides
  from leaking into production deployments.

---

## Links

- Related: ADR-001 (Runtime Authority Boundary)
