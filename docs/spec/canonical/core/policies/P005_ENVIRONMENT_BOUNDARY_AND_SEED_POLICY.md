# Policy: Environment Boundary and Seed Ownership

**Type:** IMMUTABLE CORE
**ID:** P005
**Category:** Runtime Safety / Test Isolation / Seed Governance

---

## Objective

Define explicit operational boundaries between `test`, `runtime`, and `dev/prod`
contexts, and define ownership for seed generation/reconciliation to avoid
cross-context mutation and configuration drift.

---

## Scope

This policy applies to:

1. Local execution
2. CI/CD workflows
3. Containerized checks
4. Wizard/bootstrap/generation flows

---

## Environment Contract

### Test Context

1. Repository-root `.providence` MUST NOT be mutated by tests.
2. Test writes MUST target isolated roots (`tmp_path`, `SDD_TEST_OUTPUT_DIR`, or shadow workspace).
3. Path overrides MUST NOT bypass isolation guarantees.

### Runtime Context

1. Runtime mutations under `.providence` are allowed only through governed flows.
2. Signature and trust behavior MUST follow `SDD_SIGNATURE_MODE` and keyring precedence rules.
3. Non-governed runtime mutation attempts MUST be blocked or flagged.

### Dev/Prod Context

1. Wizard/compile/deploy writes MUST resolve to declared workspace roots.
2. CWD-only fallback behavior that may target unintended roots is forbidden.

---

## Seed Ownership Policy

Managed seed artifacts (e.g. `CLAUDE.md`, `.claude/`, `.gemini/`, `.cursor/`,
`.vscode/ai-rules.md`, `.github/copilot-instructions.md`) are governed outputs.

### Allowed Owners / Triggers

1. `providence governance generate` (governed generation path)
2. Wizard generation/deployment phases in governed flows
3. Approved maintenance/reconciliation commands declared by governance

### Forbidden Behavior

1. Untracked/manual mutation in test context
2. Mutation by non-governed scripts during CI gates
3. Drift-producing writes outside approved owners/triggers

---

## Standardized Path Variables

The following variables are recognized as standardized path controls:

1. `SDD_WORKSPACE_ROOT`
2. `SDD_TEST_OUTPUT_DIR`
3. `SDD_COMPLIANCE_EVENTS_PATH`
4. `SDD_TELEMETRY_PATH`
5. `SDD_TRUSTED_KEYRING`

Precedence and fallback semantics MUST remain deterministic and context-safe.

---

## Enforcement

Compliance is enforced through CI environment-boundary gates, including:

1. `env-boundary-lint`
2. `workspace-root-resolution-check`
3. `test-isolation-preflight`
4. `repo-providence-mutation-guard` (compatibility alias: `repo-sdd-mutation-guard`)
5. `runtime-seed-drift-check`
6. `telemetry-path-scope-check`
7. `trusted-keyring-precedence-check`
8. `signature-mode-policy-check`

Warn/enforce promotion is controlled by rollout criteria documented in OpenSpec
change artifacts.

---

## Delivery Checklist

- [ ] Context (`test` / `runtime` / `dev/prod`) identified before side effects
- [ ] No repository-root `.providence` mutation from tests
- [ ] Seed writes performed only by approved owners/triggers
- [ ] Path variable usage complies with precedence/fallback rules
