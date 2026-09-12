# ADR-024 — Providence CI/CD Brand Alignment

**Status:** Accepted
**Date:** 2026-09-12
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

The Python/Go workspace has been Providence-branded since `pyproject.toml`'s
`name = "providence"` (see `git log`: "feat: change name to new brand:
providence"), but several CI/CD surfaces still displayed the pre-rename `SDD`
label or the `sdd-harness` vendor string: workflow/job names
(`SDD Mandate Validation`, `Validate SDD Governance Mandates`), step labels
(`Bootstrap SDD CLI`), Docker OCI metadata (`org.opencontainers.image.title`,
`.vendor`), the container entrypoint banner, an internal CI gate id
(`repo-sdd-mutation-guard`), and the pre-commit hook installer's user-facing
output. Mission `20260912-providence-cicd-brand-refinement`
(`.analysis/refined/20260912-providence-cicd-brand-refinement/`) diagnosed and
refined this drift.

This is a narrower, already-in-flight rename (`SDD` → `Providence`) than
ADR-023's "Providentian" identity direction — see ADR-023 § Decision, which
explicitly states the CLI binary, packages, and README "remain Providence
until a separate, explicit decision." This ADR does not touch that separate,
larger decision; it only finishes aligning CI/CD surfaces with the
**already-current** Providence brand.

## Decision

Adopt a compatibility-boundary policy for the CI/CD brand migration:

**Renamed now (public display strings, no external contract):**

- Workflow name (`.github/workflows/sdd-validation.yml`): `SDD Mandate
  Validation` → `Providence Mandate Validation`; job name `Validate SDD
  Governance Mandates` → `Validate Providence Governance Mandates`;
  concurrency group `sdd-validation-*` → `providence-validation-*`.
- Step labels: `Bootstrap SDD CLI` → `Bootstrap Providence CLI` (workflow
  files and `.github/actions/bootstrap-providence-cli/action.yml`'s own
  `name`/`description`/step names).
- Docker OCI labels (`infrastructure/docker/Dockerfile`):
  `image.title` → `Providence Agentic OS`, `image.vendor` → `providence`.
- Container entrypoint banner (`infrastructure/docker/entrypoint.sh`):
  `Starting SDD Sovereign Container...` → `Starting Providence Sovereign
  Container...`.
- Pre-commit hook installer output (`.github/setup-precommit-hook.sh`):
  all user-facing echo/comment text.
- Two latent `sdd` CLI invocations found during this pass — `RUN sdd
  governance compile` and the Dockerfile `HEALTHCHECK`/entrypoint safety-mode
  fallback (`sdd tools list`) — were **bugs**, not branding: no `sdd` console
  script has existed since the rename (`pyproject.toml` registers only
  `providence`). Fixed to `providence` as part of this same edit, since they
  live in the exact lines being touched for branding.

**Renamed now, with a compatibility alias (internal identifier, has an
existing external CLI contract):**

- CI gate id `repo-sdd-mutation-guard` → canonical `repo-providence-mutation-guard`
  in `tools/ci/environment_gates.py`. The old CLI argument value and the
  `gate_repo_sdd_mutation_guard` Python name remain callable (both now
  delegate to the canonical implementation and emit the canonical `gate`
  field in their result), so any out-of-tree caller using the old name keeps
  working. All in-repo call sites (`reusable-test.yml`, the unit test) were
  moved to the canonical name.

**Not renamed (explicit non-goals, per the refined package's Compatibility
Policy):**

- `SDD_*` environment variables (`SDD_ENFORCE_PIPELINE_CORRECT`,
  `SDD_GOVERNANCE_MODE`, `SDD_TEST_OUTPUT_DIR`, `SDD_WORKSPACE_ROOT`,
  `SDD_TELEMETRY_PATH`, `SDD_COMPLIANCE_EVENTS_PATH`, `SDD_TRUSTED_KEYRING`,
  `SDD_SIGNATURE_MODE`, `SDD_COMPILE_BIN`, `SDD_BIN`, `SDD_ALLOW_REPO_SDD_MUTATION`,
  `SDD_INSTALL_BASE_URL`, `SDD_INSTALL_DIR`, `SDD_GOLDEN_ENFORCEMENT_MODE`) —
  these are existing runtime/CI contract inputs; renaming without an alias
  would break running automation.
- `sdd-compile` binary/asset name and `tools/sdd-compile/` — compatibility-
  sensitive release artifact name; release tooling and checks are built
  around this exact string. No rename or alias introduced by this ADR.
- `.github/workflows/sdd-validation.yml`'s **filename**, and the container's
  internal `sdd` OS user/group and `/tmp/sdd-shadow-repo` shadow-copy path
  (the latter is also matched as a literal string by
  `environment_gates.py`'s `_allowed_in_test_path()`) — none of these are
  externally visible branding; renaming them would add cross-file coupling
  risk (shadow path) or required-check risk (workflow filename) for no
  user-facing benefit.
- `check_no_sdd_ci_commands.py` and other `sdd`-named tool scripts under
  `tools/ci/` — script filenames, not display branding; out of this pass's
  scope.

**Branch protection risk, explicitly accepted:** renaming the workflow's
top-level `name:` and job `name:` can change the GitHub required-status-check
label if `main`'s branch protection references the old names by string. This
environment has no `gh`/network access to verify branch protection
programmatically; the repository owner confirmed accepting this risk and
will adjust branch protection manually if a required check is found orphaned
after this change merges.

## Consequences

**Positive:**

- CI/CD-visible names (workflow/job/step labels, Docker metadata, hook
  output) now consistently read "Providence," matching the already-Providence
  package identity — no more mixed-brand confusion for maintainers or
  external consumers reading checks, image metadata, or install output.
- The internal CI gate has a canonical Providence-branded id while remaining
  callable under its old id — no forced simultaneous update of any
  out-of-tree caller.
- Two dead `sdd` CLI invocations (Docker build/healthcheck) are fixed as a
  side effect of the same edit, rather than left as a latent build/healthcheck
  failure.

**Negative:**

- If `main`'s branch protection required-status-checks reference the old
  workflow/job name literally, that required check becomes orphaned until
  someone updates branch protection to the new name (accepted risk, no
  automated verification available in this environment).
- `SDD_*` env vars, `sdd-compile`, and the workflow filename remain
  inconsistent with the Providence brand by design — a second, later ADR
  would be needed to retire them, once a deprecation/alias plan for each
  exists (see `SQ-001` in the refined mission's analysis: "Create a formal
  compatibility policy for `sdd-compile` naming").

## Alternatives Considered

- **Rename everything, including `sdd-compile`, `SDD_*` env vars, and the
  workflow filename, in one pass.** Rejected — these are compatibility-
  sensitive identifiers with real external dependents (CI scripts, release
  tooling, potentially branch protection); a single big-bang rename without
  aliases risks breaking running automation for a purely cosmetic gain.
- **Leave the internal gate id as `repo-sdd-mutation-guard` entirely,
  deferring the rename.** Rejected — the gate id is internal (only invoked
  from this repo's own workflows/tests), so renaming it now carries none of
  the external-contract risk that blocks the env-var/asset-name renames, and
  a compatibility alias costs one line.

## Links

- `.analysis/refined/20260912-providence-cicd-brand-refinement/` — analysis,
  proposal, design, tasks for this migration
- ADR-023 (`ADR-023-providentian-naming-and-identity.md`) — the separate,
  larger identity direction this ADR does not touch
- Changed files: `.github/workflows/sdd-validation.yml`,
  `.github/workflows/reusable-governance.yml`,
  `.github/workflows/reusable-test.yml`,
  `.github/actions/bootstrap-providence-cli/action.yml`,
  `.github/setup-precommit-hook.sh`, `infrastructure/docker/Dockerfile`,
  `infrastructure/docker/entrypoint.sh`, `tools/ci/environment_gates.py`,
  `tests/unit/test_environment_gates.py`,
  `docs/spec/canonical/core/policies/P005_ENVIRONMENT_BOUNDARY_AND_SEED_POLICY.md`
  (and its `packages/docs/` mirror)
</content>
