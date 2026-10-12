# RFC-019: One Environment Contract Between the Prompt-Submit Hook and the CLI

**Status:** Proposed — comment period open (M006: this is a breaking change and must
be accepted before it ships)
**Date:** 2026-10-11
**Author:** Sergio Lacerda
**Related:** ADR-025 (prompt-submit hook hardening), ADR-007 (environment variable
precedence matrix), ADR-024 (CI/CD brand alignment)

---

## Context

### Problem

The prompt-submit hook and the CLI disagree on the names of the environment variables
that connect them:

- the hook script and its launcher export and read `PROVIDENCE_WORKSPACE_ROOT`;
- every CLI and core reader of the workspace-root override reads only
  `SDD_WORKSPACE_ROOT`, and never `PROVIDENCE_WORKSPACE_ROOT`;
- the ask entrypoint marker is `SDD_ASK_ENTRYPOINT` on both sides, under the retired
  `SDD_` namespace.

Consequence: the hook's guard "an inherited value may name another project and must not
win" does not hold for the CLI. An inherited `SDD_WORKSPACE_ROOT` outranks cwd
discovery, while a `PROVIDENCE_WORKSPACE_ROOT` set by the hook (or by the user) is
ignored by the CLI.

### Current State

| Concept | Hook | CLI / core / runtime |
|---|---|---|
| Workspace-root override | `PROVIDENCE_WORKSPACE_ROOT` | `SDD_WORKSPACE_ROOT` |
| Ask entrypoint marker | `SDD_ASK_ENTRYPOINT` | `SDD_ASK_ENTRYPOINT` |

Readers of the root override: `providence_core/utils/_environment_workspace.py`,
`providence_cli/services/_governance_compile_support.py`,
`providence_cli/utils/sdd_authority.py` (through the core helper). Reader of the
entrypoint marker: `providence_runtime/intake/entrypoint.py`.

### Why This Matters

A hook that exports a variable nobody reads is silent in the same way a dead adapter is
(ADR-025). A retired name that is still honoured keeps a second contract alive.

### Scale / Scope

- Affects: `providence_core`, `providence_runtime`, `providence_cli`, `providence_wizard`
  (hook template), test isolation (`conftest.py`, `tests/conftest.py`), `tools/ci`,
  `tools/testing`, `infrastructure/docker`.
- Out of scope (narrow, ADR-025 decision U-02): every other `SDD_*` variable, the
  `[tool.sdd.*]` tables, the `[sdd]` profile section and the `sdd-*` names.

---

## Proposed Decision

### The Proposal

Make `PROVIDENCE_WORKSPACE_ROOT` and `PROVIDENCE_ASK_ENTRYPOINT` the only names for these
two concepts, and reject `SDD_WORKSPACE_ROOT` and `SDD_ASK_ENTRYPOINT` with a diagnostic
that names the replacement.

### Why This Approach?

- One name per concept on both sides removes the disagreement.
- A retired name is rejected rather than aliased or mapped (the policy of Strategist
  ADR-0063): nothing silently interprets it.
- `PROVIDENCE_WORKSPACE_ROOT` already exists in the hook launcher and template, so the hook
  side needs no rename for the root.

### Behavior

- `workspace_root_from_env()` reads `PROVIDENCE_WORKSPACE_ROOT`. When `SDD_WORKSPACE_ROOT`
  holds a value (even if the canonical one is also set), it raises
  `RetiredEnvironmentVariableError`; there is no precedence between the two.
- `resolve_ask_entrypoint()` reads `PROVIDENCE_ASK_ENTRYPOINT` and raises the same error
  for `SDD_ASK_ENTRYPOINT`.
- The CLI renders the error as `ERROR: <retired> was retired and is no longer read; set
  <replacement> instead` and exits 2, without a traceback.
- The hook exports `PROVIDENCE_ASK_ENTRYPOINT=hook` and surfaces the CLI's last stderr
  line next to its skip reason.
- The `workspace-root-resolution-check` CI gate fails with
  `RETIRED_ENVIRONMENT_VARIABLE`.
- An empty or whitespace-only retired variable is not an input.

### Forcing the new CLI

The environment contract only holds when both sides speak it, and an old CLI cannot be
changed after it ships. The hook therefore trusts an executable by what it does, never by
what it calls itself, and never injects context from one that fails:

1. **Contract echo.** The hook sets `PROVIDENCE_ASK_ENTRYPOINT=hook`; the CLI reports the
   marker it honored on the `entrypoint :` line of its output. A CLI that reports anything
   but `hook`, or no `entrypoint` line, is refused (`cli_contract_mismatch`). A CLI that
   predates this contract ignores the marker and reports `explicit_command`, which is the
   silent mislabel this RFC removes.
2. **Fingerprint.** The CLI must report a `fingerprint=` that is a prefix of the workspace's
   `fingerprints.combined`. A missing or different value is refused
   (`cli_fingerprint_mismatch`); a workspace without `fingerprints.combined` is refused
   (`workspace_fingerprint_missing`).

There is no version list, no version probe and no minimum version. The package version is
derived from release tags (`hatch-vcs`), so a number written now would be a guess, and a
list of known-bad releases is a second rule that has to be edited after every release and
that can disagree with the first. One rule needs no upkeep.

The hook also has exactly one way to resolve each input, so there is nothing to choose
between: the executable is `providence` on `PATH` (no workspace `.venv` search), the
workspace is the one whose `.providence/runtime/hooks/` holds the hook (no `cwd` guess;
otherwise `hook_misplaced`), and the workspace fingerprint is `fingerprints.combined` (no
`governance_fingerprint` alias). A missing metadata file is reported (`metadata_missing`).
The launcher names a governed workspace whose hook file is missing (`hook_missing`).

Each refusal is a named reason on stderr plus a `PROVIDENCE GOVERNANCE DEGRADED` notice
to the model; the hook still exits 0 and never blocks the prompt.

The reverse skew (old deployed hook, new CLI) fails loudly in the CLI: the old hook
exports `SDD_ASK_ENTRYPOINT`, which the CLI rejects with exit 2 and a message naming
`PROVIDENCE_ASK_ENTRYPOINT`; the hook surfaces that line next to `subprocess_error`.

---

## Alternatives Considered

### Alternative 1: Dual-read with a deprecation warning — **Rejected because**: it keeps the retired contract alive and is the `SDD_OTEL_ENDPOINT` pattern this work removes elsewhere.

### Alternative 2: Make the hook export both names — **Rejected because**: it preserves the split and hides the disagreement instead of resolving it.

### Alternative 3: Keep `SDD_*` on both sides and rename the hook's variable — **Rejected because**: it moves the hook onto the namespace retired by the brand change (ADR-023, ADR-024) and contradicts the launcher already shipped.

### Alternative 4: Refuse a list of known-bad versions, or pin a minimum one, in the hook — **Rejected because**: the release number does not exist yet, so a minimum would be a guess; a list enumerates the past, needs an edit after every release and can disagree with the echo. A number does not prove behavior; the entrypoint echo does.

### Alternative 5: Rename every `SDD_*` variable in one change — **Rejected because**: it is a wide breaking change (about 40 names) with its own inventory and RFC; it is tracked separately (SQ-02).

---

## Consequences

### Positive ✅

- The hook's root override finally reaches the CLI; the "inherited value must not win"
  guard becomes true.
- No retired name is interpreted anywhere on the hook-to-CLI path.
- A stale hook or a stale shell export fails with a message that says what to set.

### Negative ⚠️

- Environments exporting `SDD_WORKSPACE_ROOT` or `SDD_ASK_ENTRYPOINT` (CI, devcontainers,
  scripts, developer shells) stop working until renamed.
- A stale deployed hook that still exports `SDD_ASK_ENTRYPOINT` makes `providence ask`
  fail; `providence governance hook status` reports that hook as stale.
- A new hook running against an old CLI sends `PROVIDENCE_ASK_ENTRYPOINT`, which the old
  CLI ignores: the call is then treated as an explicit command. Upgrade the CLI first.

### Risks 🚨

- **Risk**: partial rollout (new hook, old CLI, or the reverse).
  - **Mitigation**: the regenerated hook refuses any CLI that does not echo
    `entrypoint : hook` (`cli_contract_mismatch`; 1.0.17 and older still read
    `SDD_ASK_ENTRYPOINT` and report `explicit_command`) and rejects context with a
    different fingerprint, so the skew is reported instead of silent. Upgrade the CLI
    before regenerating the hook.
- **Risk**: hermetic tests that set the retired name.
  - **Mitigation**: the root conftest scrubs both names; dedicated tests cover the rejection.

---

## Acceptance Criteria

- [ ] `SDD_WORKSPACE_ROOT` and `SDD_ASK_ENTRYPOINT` are rejected with the replacement named
- [ ] The CLI exits 2 with no traceback for a retired variable
- [ ] The hook exports `PROVIDENCE_ASK_ENTRYPOINT` and surfaces the CLI diagnostic
- [ ] The hook refuses a CLI that does not echo `entrypoint : hook` (`cli_contract_mismatch`)
- [ ] The hook has no version list or probe and no second source for the CLI, the workspace root or the fingerprint
- [ ] The retired names appear in package source only in the modules that reject them
- [ ] ADR-007 and policy P005 list `PROVIDENCE_WORKSPACE_ROOT`
- [ ] CHANGELOG `[Unreleased]` records the breaking change with its migration

---

## Migration

```bash
# Before
export SDD_WORKSPACE_ROOT=/path/to/workspace
SDD_ASK_ENTRYPOINT=hook providence ask "..."

# After
export PROVIDENCE_WORKSPACE_ROOT=/path/to/workspace
PROVIDENCE_ASK_ENTRYPOINT=hook providence ask "..."
```

Order: upgrade the CLI, rename the variables in CI and shells, then regenerate the hook
(`providence governance generate`) and confirm with `providence governance hook status`.

---

## Implementation Plan

1. `providence_core`: add the canonical and retired names, `RetiredEnvironmentVariableError`
   and `reject_retired_environment_variable`; make `workspace_root_from_env` use them.
2. `providence_runtime`: switch the entrypoint marker and reject the retired one.
3. `providence_cli`: use the core reader in the output-base resolution; render the error
   in `main()`.
4. `providence_wizard`: export `PROVIDENCE_ASK_ENTRYPOINT` from the hook template and
   verify the CLI's `entrypoint` echo, version and fingerprint before injecting context.
5. `tools/ci`, `tools/testing`, `infrastructure/docker`, conftests: rename; add the gate rule.
6. Update ADR-007, P005 and the M015 runbook; add the CHANGELOG entry.
