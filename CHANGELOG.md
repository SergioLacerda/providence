# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Commit convention:** New entries should follow [Conventional Commits](https://www.conventionalcommits.org/).
> Automation with `git-cliff` or `commitizen` can generate entries from commit messages.

---

## Release Checklist

Before tagging a new release, verify:

- [ ] `make release-dry-run` passes with no errors
- [ ] `make release-prepare VERSION=x.y.z` run and reviewed — renames `[Unreleased]` to `[x.y.z] — YYYY-MM-DD` in `CHANGELOG.md` and updates the pinned install tag in `README.md`
- [ ] `readme-client.md` — client-facing install instructions reflect current CLI commands
- [ ] `readme-detailed.md` — detailed architecture description matches current packages and structure
- [ ] `readme-ia.md` — AI/agent context is accurate for the new release
- [ ] Git tag created: `git tag vX.Y.Z && git push origin vX.Y.Z`

---

## [Unreleased]

## [1.0.15] — 2026-09-13

### Fixed
- Fixed a CodeQL "unused import" false positive in `phase6_output_validator.py`
  by declaring its intentionally re-exported names (kept for backward
  compatibility and guarded by a cross-module sync test) in `__all__`,
  instead of relying on a `# noqa` comment CodeQL doesn't recognize.
- Fixed the "Container Security (Trivy)" CI job failing with "Username and
  password required" when `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN` secrets
  aren't configured — the Docker Hub login step now skips cleanly instead
  (the container build and scan still work unauthenticated; only the
  anonymous-pull rate limit is affected).
- Fixed an invalid workflow expression introduced by the above: the
  `secrets` context is not permitted inside `if:` conditionals. The two
  secrets are now mirrored into job-level `env` vars first, and the `if:`
  reads from `env` instead.
- Fixed the release pipeline's upgrade/rollback smoke test failing with
  "No providence_cli-*.whl asset found" when the previous published release
  predates the `sdd_cli` → `providence_cli` package rename. That one
  boundary release (`v1.0.13`) publishes the wheel under the old
  distribution name; the smoke test now skips the upgrade/rollback
  assertion for this specific, one-time transition instead of failing the
  release, since a force-reinstall across a package rename would not be a
  real rollback test anyway.

## [1.0.14] — 2026-09-12

### Changed
- Rebranded the project and CLI from `sdd` to `providence`, including core
  infrastructure, pipeline orchestration, and governance documentation.
- Extended the managed-block convention (preserving hand-edited content
  during regeneration) to Copilot and Antigravity instructions files.

### Added
- Added post-merge and pre-push git hooks to the tools scripts.

### Fixed
- Fixed handshake strict-mode exit propagation and drift-detection logic to
  compare against previous session states.
- Fixed repo-root resolution to avoid falling back to the harness source
  directory, and added validation for empty client governance artifacts.

## [1.0.13] — 2026-09-02

### Fixed
- Fixed Windows compatibility for Make targets by moving shell-sensitive
  recipes into `tools/maintenance/make_tasks.py`, including `help`,
  `golden-status`, docs serving, Docker build setup, Go lint/build wrappers,
  and web commands.
- Fixed `release.prepare` version forwarding so `make release.prepare vX.Y.Z`
  and `make release-prepare X.Y.Z` normalize to the release script's required
  `X.Y.Z` format.
- Fixed Windows path and symlink portability regressions in CI/dev tooling,
  including GitHub Actions freshness scans, governance readable-source drift
  checks, and Python mutation-test workspace links.
- Fixed governance compilation source precedence so the v3
  `mandates/mandates.md` source cannot be shadowed by stale legacy
  `mandate.md` content.

## [1.0.12] — 2026-08-26

> `v1.0.11` was tagged but its release workflow failed the same way `v1.0.9`
> did — the `CHANGELOG.md` validation gate rejected it because `[Unreleased]`
> had no entries yet when the version header was created, so the extracted
> release notes were empty (`tools/release/prepare_release.py` now refuses to
> do this). No GitHub Release or published artifacts exist for it.

### Added
- Added `make release-prepare VERSION=x.y.z`, automating the `CHANGELOG.md`
  `[Unreleased]` → `[x.y.z]` version-header rename and the `README.md`
  pinned-install-tag update steps of the Release Checklist above
  (`tools/release/prepare_release.py`).

### Fixed
- Corrected mandate M006's canonical title in
  `docs/spec/canonical/guides/M006_RFC_PROCESS.md` — it leaked the full Goal
  sentence into the heading instead of a short title, causing the compiled
  governance artifact's M006 title to diverge from its golden fixture.

## [1.0.10] — 2026-08-25

> `v1.0.9` was tagged but its release workflow failed before completing — the
> `CHANGELOG.md` validation gate rejected it because this file had no
> `[1.0.9]` section yet (see Fixed below for the gate itself). No GitHub
> Release or published artifacts exist for it. This release supersedes it,
> the same way `[1.0.8]` superseded `[1.0.5]`–`[1.0.7]`.

### Added
- Added a Devin plugin generator and `sdd devin` CLI command for
  soft-standalone governance projections, with specialized governance rules,
  project-level configuration templates, and governance summary snapshots
  integrated into its generated output.
- Added `--language` support to `providence init`, persisting and bridging the
  user's language preference across the generated workspace.
- Added `GateLatencyCollector` to track guardrail latency metrics, with the
  underlying percentile math modularized into its own helper.
- Added `security-freshness.yml`, an independent weekly-scheduled run of the
  same security suite as `reusable-security.yml` (govulncheck, pip-audit,
  bandit, container scan), so a CVE disclosed against an otherwise-unchanged
  dependency doesn't wait for the next push to be caught.
- Added a `uv lock --check` preflight step to `health.yml`'s
  `environment-preflight` job, failing fast when `uv.lock` drifts out of sync
  with `pyproject.toml` instead of surfacing confusingly in downstream jobs
  (this is the class of bug that produced the two Fixed entries below).

### Changed
- Decomposed `providence-cli`'s CLI commands into modular sub-apps, and its `init`
  orchestration into modular services, adding telemetry and `ask-backend`
  pipeline enhancements along the way.
- Bumped dependencies across the workspace (`crewai`, `setuptools`,
  `hatchling`, `mypy`, `ruff`, `python-dotenv`, `hypothesis`, `types-PyYAML`,
  the Go toolchain, GitHub Actions, and the landing app's npm packages) via
  Dependabot.

### Fixed
- Fixed the Docker build's `setuptools==83.0.0` pin drifting out of sync with
  `pyproject.toml`'s `constraint-dependencies` (bumped to `>=84.0.0` for
  PYSEC-2026-3447 by a Dependabot update that never touched the Dockerfile):
  both build stages now pin `84.0.0` and the final Trivy-facing metadata gate
  bans `83.0.0` alongside the older `70.3.0`/`1.1.2`; `uv.lock` was relocked
  to match.
- Fixed a `mypy` `unused-ignore` error on `tools/verify_mkdocs_paths.py`'s
  `add_multi_constructor` call — the `types-PyYAML` bump above shipped a
  properly typed stub, making the existing `# type: ignore[no-untyped-call]`
  obsolete.
- Fixed `release-install-smoke` failing on `macos-latest` with `No matching
  distribution found for pyyaml` — the release wheelhouse download step only
  ever targeted `manylinux2014_x86_64` and `win_amd64`, so no
  platform-specific dependency wheels (e.g. PyYAML) existed for macOS's
  offline `pip install --no-index` smoke install. Added a
  `macosx_11_0_arm64` download target alongside the existing two.

## [1.0.8] — 2026-08-09

> `v1.0.5`, `v1.0.6`, and `v1.0.7` were all tagged but their release
> workflows failed before completing (see Fixed below) — no GitHub Release or
> published artifacts exist for any of them. This release supersedes all
> three, the same way `[1.0.3]` superseded `[1.0.2]`.

### Added
- Added multi-platform installation scripts (`install.sh`, `install.ps1`) and a
  `reusable-release-build.yml` workflow that builds and publishes the `sdd` CLI
  as standalone PyInstaller binaries across platforms.
- Added a module-size complexity budget: `tools/architecture/validate_class_size.py`
  becomes a blocking gate (with `tools/architecture/module_size_allowlist.json`
  grandfathering pre-existing exceptions), formalized in
  `docs/adr/ADR-019-guardrail-complexity-budget.md` to keep the repository's own
  governance/guardrail surface itself bounded.
- Added a Docker build gate that removes stale Python package metadata
  (`msgpack`, `setuptools`) left behind by intermediate build layers, so a
  full-filesystem Trivy scan of the final runtime image cannot resurface a
  version that was already patched out earlier in the build.

### Changed
- Migrated Docker builds from plain `docker build` to BuildKit/buildx
  (`docker buildx build --load`), in both the `Makefile`'s `docker-build`
  target and the `reusable-security.yml`/`reusable-test.yml` CI jobs.
  `.dockerignore` now also excludes `node_modules/`, and build-time caches
  (`uv` cache, `pip`) are stripped from the final image to reduce layer bloat.
- Reorganized the root `Makefile` into affinity-grouped `mk/*.mk` includes
  (python, lint, docs, web, go, release, docker, misc) with a self-documenting
  `help` target, plus additive namespaced aliases (e.g. `make test.fast`,
  `make docker.build`) for every existing target. No existing target name,
  recipe, or CI/documentation reference changes.
- Standardized Dependabot grouping/configuration and cleaned up internal
  import styles across the `providence_runtime` and `providence_cli` packages.
- Simplified `providence_core`'s TOML backend imports, taught
  `tools/ci/check_no_sdd_ci_commands.py` to ignore comments when scanning for
  disallowed CI commands, and added `--all-packages` to the `uv-sync-retry`
  GitHub Action.

### Fixed
- Fixed a circular import between `providence_cli`'s ask-backend helpers/response
  service and `ask_hash` by removing a redundant re-export; also added a
  Docker build-time check that fails the build if a known-vulnerable
  `msgpack`/`setuptools` version resurfaces at runtime.
- Fixed the production Docker image's `COPY` instruction order overwriting the
  pre-built virtualenv with the repository's own local `.venv` when one
  existed at build time, by copying the source tree before the builder-stage
  `.venv`; added a regression test guarding the ordering.
- Fixed the container image running as a named, non-numeric user (`USER sdd`)
  with a shell-form `HEALTHCHECK`, both flagged by security scanning — it now
  runs as numeric UID `1000` with an exec-form healthcheck, with unit test
  coverage added for both.
- Fixed `tools/docs/check_links.py` raising `ModuleNotFoundError: No module
  named 'providence_core'` whenever workspace packages aren't installed as editables
  — added the same `sys.path` guard `tools/maintenance/lint_all.py` already
  uses.
- Fixed `make docs-build`'s selector-compiler step and the pre-commit hook's
  canonical spec-lint step failing the same way (`No module named
  'providence_wizard'`/`'providence_cli'`) when invoked via `python -m`, which can't use a
  per-script `sys.path` guard — both now export a `WORKSPACE_PYTHONPATH`
  matching `pyproject.toml`'s own pytest `pythonpath` list.
- Fixed `PREV_WHEEL_NAME: unbound variable` in `release.yml`'s "Upgrade/
  rollback smoke" step: the previous release's tag/wheel name/URL were
  written to `$GITHUB_ENV` (which only takes effect in *later* steps) and
  then read back within the same step — this failed on every OS, not just
  Windows, and had never been exercised by a real release before `v1.0.5`.
  Now captured into a local env file and `source`d in the same shell.
- Fixed `providence --version` (`Error: No such option '--version'`) — the flag was
  never implemented, despite a release-smoke step assuming it existed. Added
  it as an eager option resolving the real installed version via
  `importlib.metadata`, and fixed the separate `providence version` subcommand's
  hardcoded `1.0.0` output the same way.
- Fixed a broken doc link to `governance_fetcher.py` (deleted in an earlier
  refactor, commit `e75bf5d`) in `ADDING_NEW_PROJECT.md`.
- Added a missing mypy override for `questionary` (optional wizard dependency
  with no bundled type stubs), matching the existing `msgpack`/`httpx`/
  `crewai` overrides.
- Extended the Makefile guardrail tests (`test_makefile_guardrails.py`,
  `test_release_workflow_policy.py`) to scan `mk/*.mk` after the Makefile
  split, so the "no inline `python -c`/`sh -c`" and selector-artifact checks
  keep covering the full effective Makefile instead of just the root file.
- Fixed `release.yml`'s "Upgrade/rollback smoke" step installing the previous
  release's wheel without `--force-reinstall`: `providence-cli` was already
  installed at the new dist version from an earlier step, so plain `pip
  install` saw the requirement as already satisfied and silently skipped the
  downgrade (`ERROR: expected previous version 1.0.4, got 1.0.6`) instead of
  actually testing the rollback path. Adding `--force-reinstall` alone then
  surfaced a second issue in the same step: `.release-smoke/prev` only
  contains the single downloaded previous-version wheel, not a full
  dependency closure like `dist/` has (`reusable-release-build.yml` vendors
  every transitive wheel there), so `--force-reinstall` tried to also
  reinstall `click`/`pyyaml`/`rich`/etc. from that same directory and failed
  (`No matching distribution found for click>=8.3.3`). Added `--no-deps`
  alongside `--force-reinstall` for both the initial downgrade and the later
  rollback in that step, verified against a throwaway dummy-package
  reproduction before applying.
- Fixed `tools/release/resolve_vcs_version.py` raising `ModuleNotFoundError:
  No module named 'providence_core'` when invoked as `python -m
  tools.release.resolve_vcs_version` (as `release.yml`/`Makefile` do) without
  `providence_core` installed as an editable — it was the one script in
  `tools/release/` missing the `sys.path` guard already caught by
  `test_release_scripts_module_invocation.py`'s regression test. Also
  hardened `test_skills_dry_run_module_entrypoint_preserves_exit_code` (a
  separate test spawning `python -m providence_cli ...` as a real subprocess, which
  does not inherit pytest's own `pythonpath` sys.path injection) to forward
  the same workspace `PYTHONPATH` explicitly, instead of depending on
  `providence_cli` being installed in whichever venv runs the suite.

## [1.0.4] — 2026-07-31

### Fixed
- Fixed `providence audit` drift-rate calculations inflating detected-drift counts
  by roughly 7x: `governance.ask.phase` sub-events (each `providence ask`
  invocation emits ~6) inherit `drift_detected` from their parent
  `governance.ask` event, and were being counted as independent drifts in
  both the base summary and the windowed correlation calculation. A new
  `_is_ask_phase_event()` predicate excludes phase sub-events from the
  drift-rate numerator in both calculations, while the denominators
  (ask-event totals) keep counting them — the same scoping principle
  applied to the `token_comparison` denominator fix in `[1.0.3]`, now
  applied to drift *counts*.
- Fixed the release smoke test creating its client project
  (`git-smoke-project`) inside the checked-out repository, which is itself
  an SDD workspace (`.providence/` is committed) — `providence init`'s nested-workspace
  guard could treat the checkout as a blocking parent workspace. Both
  `release.yml` and `release-dry-run.yml` now create the smoke project
  under `$RUNNER_TEMP` instead. Also fixed two related regressions
  surfaced by the same investigation: `providence init`'s parent-workspace guard
  now requires `.providence/profile` to exist before treating a directory as a
  blocking workspace (a bare `.providence/`, such as the compiler-binary cache at
  `~/.providence/bin`, no longer falsely blocks `providence init`), and
  `ask_telemetry`'s fallback token estimator no longer returns `0` — which
  downstream telemetry cannot distinguish from "no measurement" — for
  non-empty query/output text shorter than 4 characters; it now floors at
  `1`.

## [1.0.3] — 2026-07-20

### Fixed
- Fixed standalone `providence governance compile`/`providence governance generate` failing
  with "No sdd-compile release binary found" for any install built from a dev
  checkout between two release tags. `hatch-vcs`'s default version scheme
  (`guess-next-dev`) reports dev builds under a *guessed, unreleased* next
  version (e.g. `1.0.4.dev12+g...` for a checkout 12 commits past the `v1.0.3`
  tag) rather than the actual last release — so `CompilerRunner`'s dev-version
  fallback (added in a prior release) was trying to download a binary from a
  GitHub release tag (`v1.0.4`) that never existed. All 9 workspace packages
  now use the `no-guess-dev` version scheme, so dev builds report a version
  derived from the real last tag (e.g. `1.0.3.post1.dev0+g...`), which the
  existing fallback logic already resolves correctly.
- Fixed the `v1.0.2` `sdd-compile` release binaries reporting a hardcoded
  `0.2.0` placeholder version (a leftover from before release builds injected
  the real version via `-ldflags`), which broke the CLI↔binary version
  handshake for every fresh install that falls back to downloading a release
  binary — including the documented `uv tool install git+https://...`
  onboarding flow from an unpinned branch ref, on every platform. `v1.0.2` was
  never fixable in place (release assets are immutable); this release
  supersedes it as the version the dev-build fallback resolves to.
- Fixed standalone `providence governance generate` for wizard/client installs that use
  a development `providence-cli` version without matching GitHub release assets by
  staging native `sdd-compile` binaries into the `providence-core` wheel during the
  release build and resolving packaged binaries before attempting release
  downloads. The staged package assets are generated by the release pipeline,
  not committed source files.
- Fixed the release build failing with `ModuleNotFoundError: No module named
  'tools'`: `tools/release/*.py` scripts that import from sibling modules
  (e.g. `stage_packaged_compiler_assets.py` importing
  `validate_release_assets.py`) were being invoked as bare scripts
  (`python tools/release/foo.py`) in `release.yml` and `release-dry-run.yml`,
  which puts the script's own directory on `sys.path` instead of the repo
  root. All invocations now use module form (`python -m
  tools.release.foo`), and a regression test exercises every script in the
  directory the same way CI does to catch this class of bug going forward.
- Fixed the release dry-run failing on every run with a wheel/tag version
  mismatch: neither dry-run trigger path (a manual candidate tag, or an
  automatic push to `main`) has a real Git tag at checkout time, so
  `hatch-vcs` can never resolve exactly the placeholder version being
  validated. The reusable build workflow now takes a `verify-exact-version`
  input (default `true`) that the dry-run explicitly disables.

### Changed
- **`providence audit` token metrics are now scoped to `governance.ask` invocations.**
  Previously `token_comparison.events_missing_tokens` (and the "events without
  tokens" summary line) counted every event in the compliance log, including
  `governance.ask.phase` latency sub-events and compile/lifecycle events that
  never carry token telemetry — reporting ~87% "missing" on healthy data. The
  denominator is now parent `governance.ask` events only; the JSON payload
  gains `token_comparison.ask_invocations` and
  `token_comparison.non_token_events`, and the text summary reads
  "ask invocations without tokens: N (of M)". The correlation windows'
  `token_coverage` uses the same scoped denominator, so windows are no longer
  structurally pinned to `INCONCLUSIVO`/`LOW` confidence by the token-coverage
  gate. Consumers of `events_missing_tokens` should expect the value to drop
  accordingly (semantics change, same field name).
- Migrated all 9 workspace packages to `hatch-vcs` dynamic versioning
  (previously only `providence-cli` used it; the other 8 had a static `version =
  "..."` rewritten in place by `tools/release/sync_versions.py`, which is now
  removed). Every package resolves its version directly from the release tag
  at build time; the release workflow verifies this by matching each built
  wheel's filename against the tag instead of grepping `pyproject.toml`.
  Removing the in-place rewrite also removed the need for the
  `SETUPTOOLS_SCM_PRETEND_VERSION` workaround that compensated for the dirty
  working tree it left behind.
- `providence_core`'s package build now produces wheel-only distributions (no
  sdist): its governance spec files (`mandate.spec`, `guidelines.dsl`) are
  symlinks to a shared `_spec/` directory, and a stray broken symlink
  (`spec.CANONICAL.link`) made `hatchling`'s default sdist fail during
  extraction. No sdist is published or consumed anywhere in this pipeline, so
  building wheel-only sidesteps the problem without restructuring the
  symlinks.
- Extracted the build steps shared by `release.yml` and `release-dry-run.yml`
  (cross-compiling `sdd-compile`, staging compiler assets, building every
  package, downloading the runtime wheelhouse, compiling governance
  artifacts) into a new reusable workflow,
  `.github/workflows/reusable-release-build.yml`. The two workflows had
  drifted into near-duplicate step lists, which is how the module-invocation
  bug above ended up needing to be fixed in two places.
- `release-dry-run.yml` now also runs automatically on every push to `main`
  (previously `workflow_dispatch`-only), so the full release build is
  validated continuously instead of only being caught the first time someone
  pushes a real tag. Requires marking the dry-run job as a required status
  check on `main`'s branch protection rule (manual GitHub configuration, not
  enforced by any workflow file — see
  `docs/guides/release/RELEASE_READINESS_V1.md`).
- `container-release.yml` now verifies a GitHub Release already exists for
  the target tag before publishing an image via manual `workflow_dispatch`,
  so a container can no longer be published for a tag whose `release.yml`
  build never succeeded.

## [1.0.2] — 2026-07-16

### Added
- `check_module_available()` (in `providence_core.utils.process`) and `require_dev_module()` (in `providence_cli.utils.dev_deps`): governance-safe (no `python -c`) checks that give an actionable error instead of a raw `ModuleNotFoundError` traceback when an optional dev tool (`ruff`, `mypy`, `bandit`, `build`) or the `providence_cli` package itself is missing from the active interpreter, applied to `providence lint`, `providence audit` (compliance pack), and `providence release`.

### Changed
- Breaking change: `providence_runtime.SkillEngine` no longer accepts legacy short skill aliases (for example `diagnose`, `validate-governance`); only canonical `sdd-*` names are valid, and legacy alias calls now return `legacy_alias_removed` with a canonical-name suggestion.
- Promoted `uv run providence setup run` as the primary cross-platform local-setup path in `README.md` (works without a pre-existing `.venv` or shell activation on Linux, macOS, and Windows); `make install` is documented as the CI/automation equivalent. Added a PATH-shadowing warning for contributors who also have `providence-cli` installed globally via `uv tool install`.
- Fixed `Makefile`'s `VENV_PYTHON` detection to also find `.venv/Scripts/python.exe` (Windows venv layout), not just `.venv/bin/python`.

### Removed
- Removed `install.sh` and the legacy `curl | sh` global-install instructions from `README.md` and `docs/guides/CLIENT_ONBOARDING.md`, to avoid ambiguity with the local/`uv`-based install paths.
- Removed client-facing Git hook/pre-commit setup from `providence setup`, `providence init --default`, wizard seedling selection, and generated templates.

---

## [1.0.1] — 2026-07-10

### Fixed
- Fixed release workflows to invoke the canonical `providence governance compile --profile client` command and prepare `generated/client/build/final-template/.providence` before copying generated governance artifacts.
- Added release wheelhouse dependencies for offline `pip install --no-index --find-links dist providence-cli` smoke tests on Linux and Windows.
- Fixed standalone `providence init --default` compiler execution by authorizing official platform-suffixed `sdd-compile-*` release assets as governed compiler binaries.
- Fixed wizard cleanup reporting when standalone install smoke uses a project root outside the generated client build directory.

---

## [0.1.0] — 2026-05-09

### Added
- `providence init` command — initialises workspace `.providence/profile` (INI, schema v1) with `--type`, `--name`, `--force` flags; guards against nested workspace creation
- `providence runtime status` command — shows AHP (Agent Handshake Protocol) + GAP (Governance Activation Protocol) state with exit codes per AHP state
- `providence governance score` subcommand — weighted governance score formula (profile 30 + artifacts 30 + AHP confidence 20 + core_hash 20 = 100); `--verbose` table, `--threshold` gate
- `providence doctor run --score-threshold` — aborts if score falls below threshold before running spec diagnostics
- `providence governance generate` now writes `.github/copilot-instructions.md` from real governance content (MANDATEs, GUIDELINEs, DECISIONs)
- `providence governance compile` now persists `core_hash[:16]` into `.providence/profile` after compilation
- `governance_gate()` injected into `LazyCommandGroup.invoke()` — runs AHP on every CLI invocation (exempt: `init`, `version`, `help`)
- `providence_core.governance.compliance` — append-only JSONL audit log at `.providence/runtime/compliance-events.jsonl`; events: `WORKSPACE_INIT`, `GOVERNANCE_CHECKED`, `COMPILE_COMPLETE`, `VIOLATION`
- `providence_core.governance.handshake` — canonical AHP implementation migrated from `tools/`; `tools/governance/agent_handshake.py` becomes a thin wrapper
- `providence_core.utils.environment`: `WorkspaceNotInitializedError`, `ProfileContext`, `find_workspace_root()`, `resolve_profile()`, `write_profile()`
- `SECURITY.md` — vulnerability disclosure policy and response timeline
- `conftest.py` (root) — `pytest_sessionstart` hook ensures governance compiled artifacts exist before any test session
- `make coverage` target — HTML + terminal-missing report
- `make docs-build` / `make docs-serve` targets — MkDocs build and live preview
- `make docker-build` target
- `make release-dry-run` target — validates version, git tags, and CHANGELOG before release

### Changed
- `make check` now invokes `pytest tests packages` directly (previously `python3 scripts/run_all_tests.py`)
- `--import-mode=importlib` and all `--ignore-glob` flags moved from `scripts/run_all_tests.py` into `[tool.pytest.ini_options] addopts`
- `providence doctor run` now exits 1 with an actionable message when invoked outside an initialised workspace
- `LazyCommandGroup.invoke()` raises `click.UsageError` on `WorkspaceNotInitializedError` (was silently swallowed)
- `[tool.ruff.lint.mccabe] max-complexity` lowered from 10 → 7
- Root package version bumped from `0.0.0` → `1.0.0` to align with package sub-versions
- `bandit -r packages/ -ll -q` added to `make lint`

### Removed
- `pylint` dependency and `[tool.pylint.*]` configuration (superseded by ruff)
- `"build"` removed from `[tool.uv.workspace].members` (dead entry, namespace collision risk)
- `.spec.config` as profile source — replaced by `.providence/profile` (INI schema v1)

### Fixed
- AHP `_extract_governance_core()` now searches `generated/*/compiled/` (was wrong path)
- AHP fingerprint uses `[:16]` slice (was `[:8]`, causing hash mismatches)
- AHP Layer 4 checks `generated/*/compiled/` directories
- AHP cache I/O errors now logged as warnings instead of silently suppressed
- `SDD_AGENT_ID` environment variable now respected in AHP

---

## [1.0.0] — 2026-01-01

Initial stable release of the multi-package workspace structure.

- `providence_core`, `sdd_compiler`, `providence_telemetry`, `providence_integration`, `providence_cli`, `providence_wizard` as separate uv workspace members
- Governance spec compilation pipeline (`GovernanceOrchestrator` + `DeploymentManager`)
- Agent Handshake Protocol (AHP) v1 — 4-layer validation, 5 states
- `providence lint spec`, `providence governance compile`, `providence governance generate`, `providence doctor run`
- MkDocs documentation site

[Unreleased]: https://github.com/SergioLacerda/providence/compare/v1.0.4...HEAD
[1.0.4]: https://github.com/SergioLacerda/providence/releases/tag/v1.0.4
[1.0.3]: https://github.com/SergioLacerda/providence/releases/tag/v1.0.3
[1.0.2]: https://github.com/SergioLacerda/providence/releases/tag/v1.0.2
[1.0.1]: https://github.com/SergioLacerda/providence/releases/tag/v1.0.1
[0.1.0]: https://github.com/SergioLacerda/providence/releases/tag/v0.1.0
[1.0.0]: https://github.com/SergioLacerda/providence/releases/tag/v1.0.0
