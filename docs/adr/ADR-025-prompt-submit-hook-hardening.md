# ADR-025 — Prompt-Submit Hook Hardening

**Status:** Accepted (decisions); implemented, prepared for release v1.0.18 (tag pending)
**Date:** 2026-10-11
**Deciders:** Sergio Lacerda
**Supersedes:** N/A
**Related:** ADR-024 (CI/CD brand alignment), ADR-022 (managed-block seed convention),
RFC-019 (hook and CLI environment contract)
**Source package:** `.analysis/refined/20261011-skill-hook-runtime-sdd-removal-hardening-r3/`

---

## Context

The prompt-submit hook injects governance context into Claude, Codex, Gemini and
Copilot sessions. A diagnostic of this workspace found that the hook was a
silent no-op for Claude, Codex and Gemini:

- the three adapters (`.claude/settings.json`, `.codex/config.toml`,
  `.gemini/settings.json`) ran
  `sh -c 'hook=$1; if [ -f "$hook" ]; then exec python3 "$hook"; fi; exit 0' sh
  /…/generated/client/compiled/.providence/runtime/hooks/prompt-submit.py`;
- that path does not exist, and the `[ -f ]` guard turned the miss into `exit 0`;
- `providence governance hook status` still reported the adapters as
  `configured (stale)`, because it matches substrings instead of resolving the
  target.

### How the dead command came to exist

| Commit / release | Effect |
|---|---|
| `6a3c6ee` (2026-09-13) | Introduced the `hook=$1` command with an absolute path |
| `v1.0.14` to `v1.0.16` | Shipped it; the globally installed `providence-cli` 1.0.16 still emits it |
| `3a6a623` (2026-09-15), `v1.0.17` (2026-09-16) | Replaced it with a relocatable POSIX `sh -c` launcher |
| `435d441` (2026-09-20) | Replaced that with a cross-shell Python launcher; **unreleased** |

An earlier analysis attributed the fix to `6a3c6ee`; the release wheels and tag
containment show that commit is the cause, not the fix.
`~/.local/bin/providence` resolves to the 1.0.16 install and is first on PATH, so
it is both the generator that wrote the dead commands and the CLI the hook
executes. `v1.0.17` repairs POSIX only: its launcher needs `sh`, its hook
template still uses `setdefault` for the workspace root, hardcodes the event
name and does not support Copilot.

### Other defects found in the mechanism

- Legacy acceptance on the hook and seedling path (`sdd-governance-inject.py`,
  an `is_legacy` Codex block branch, pre-rebrand cursor-rule filenames).
- The hook exports `PROVIDENCE_WORKSPACE_ROOT` while the CLI reads only
  `SDD_WORKSPACE_ROOT`.
- Every degradation path of the hook is silent; the CLI is resolved PATH-first
  with a `.venv` fallback and no version or fingerprint check.
- The generator replaces a malformed `settings.json` with `{}` plus its own keys.
- Platform timeouts written by the generator equal the hook's own 10 s.
- The `bootstrap-fallback/` template tier duplicates nine primary template paths,
  four of them divergent, and `_template_base` silently returns the last
  candidate.

### Platform facts (official documentation, fetched 2026-10-11)

- Gemini `BeforeAgent`, Codex `UserPromptSubmit` and both Copilot forms deliver
  a `prompt` field.
- Codex runs a project hook only after the operator reviews and trusts the exact
  definition. Trust is recorded against the hook's hash, so new or changed hooks are
  skipped until reviewed again in `/hooks`; Codex prints a startup warning when hooks
  need review, and project-local hooks load only when the project `.codex/` layer is
  trusted (official hooks page, fetched 2026-10-12).
- Copilot CLI selects the payload format by event-name casing. For the camelCase
  `userPromptSubmitted` form the only listed output is `modifiedPrompt`, and
  config-file command hooks for it have their output dropped. Consumption of
  `additionalContext` for the PascalCase form is not documented.
- VS Code documents `command`, `windows`, `linux`, `osx`; Copilot CLI documents
  `bash`, `powershell`, `command`. Neither documents unknown properties on an
  entry.
- Devin CLI (docs.devin.ai, fetched 2026-10-12) reads `.devin/hooks.v1.json` (top-level
  events, no wrapper), `.devin/config.json`, `.claude/settings.json` and others;
  `UserPromptSubmit` delivers `prompt` and accepts
  `hookSpecificOutput.additionalContext`; exit 2 blocks and other non-zero codes only
  log; `DEVIN_PROJECT_DIR` is set; `.claude/` hooks load by default. Not documented:
  the hook's working directory, the Windows shell, a trust prompt, and how hooks from
  several files are combined.

## Decision

Scope is the hook mechanism and its two environment variables (workspace root
and ask entrypoint). The wide legacy vocabulary is out of scope.

1. **Retired input is rejected, with no migration shim.** Remove the legacy
   markers, the `is_legacy` branch and the pre-rebrand filename acceptance. A
   file carrying a retired marker yields a deterministic diagnostic naming the
   file and the regeneration command.
2. **Adapter health comes from the real target and a content digest.**
   `hook status` resolves the command's target, compares the deployed hook with
   the template digest and exits non-zero on a broken, stale or legacy adapter.
   `governance generate` and `governance validate` are not extended.
3. **The hook stays non-blocking but is never silent.** Each skip path has a
   named reason; non-intentional reasons emit one compact diagnostic. Exit
   status stays 0. Platform timeouts are set larger than the hook's own.
4. **One environment contract.** Hook and CLI share one resolver and one name per
   concept; retired names are rejected, not aliased. The root the hook resolves
   from its own location wins over an inherited value.
5. **Generated output is derived and checked.** The `final-template` build
   records the generator source digest and deploy refuses a mismatch.
6. **The executable that runs the hook is verified by behavior.** It must echo the
   entrypoint marker it was sent and report the workspace governance fingerprint.
   There is no version list or probe, and each input (executable, workspace root,
   fingerprint) has exactly one source, so the hook has no fallback to choose
   between. A CLI that predates the contract is refused by the echo, not by name.
7. **Merging into a user settings file fails closed.** A malformed file is left
   byte-identical and a diagnostic is emitted.
8. **The launcher works on Linux and Windows** and the committed tracked file does
   not encode the generating OS. The option (the Python launcher in source, a
   `command`-only form, or per-OS keys) is chosen from evidence, after testing
   the Windows shells and whether both Copilot products accept an entry carrying
   both key sets.
9. **Copilot CLI injection is decided, not assumed.** It is not guaranteed; the
   runbook and `hook status` state it, the hook does not report success for a
   form it cannot verify, and rewriting the user's prompt through
   `modifiedPrompt` is rejected as a default.
10. **Codex trust is part of the contract.** Generation output and the runbook
    state that a changed definition is skipped until it is reviewed again in
    `/hooks` (documented behavior; not yet observed on a machine, see V-02).
11. **The `bootstrap-fallback` tier is removed.** The four divergent files are
    regenerated into the primary templates (user decision), then the tier and the
    silent last-candidate return are removed.
12. **The ADR and the runbook are tracked documents under `docs/`**, with copies
    produced under `.analysis/` by the accepted side quests. All copies state the
    same decisions.
13. **Side quests are checked for an executor before the gate.** An accepted
    `OA-CHEST` has no execution resolver in the Strategist and blocks execution
    entry; it is declined. This is a Strategist defect, outside this repository.
14. **Devin CLI is a hook platform with exactly one registration.** Devin documents
    `.devin/hooks.v1.json` (events at the top level, no wrapper) and loads
    `.claude/settings.json` hooks by default. The generator writes the Claude
    adapter's file when Claude is generated and `.devin/hooks.v1.json` only
    otherwise; a managed entry left in the Devin file is removed when Claude takes
    over. `hook status` reports a second registration as `broken` instead of
    guessing how Devin merges them. The launcher anchors on the documented
    `DEVIN_PROJECT_DIR`, never on an undocumented working directory.

User decisions taken at the approval gates (2026-10-11, refined 2026-10-12): narrow
scope; validation limited to `hook status`; Linux and Windows; verify the executable
(first by version and fingerprint, then by behavior with no fallback or
backward-compatibility branch, to avoid ambiguity);
both rebuild the local build output and fix the generator; wide vocabulary and the
OTEL, managed-block and trust-migration shims out of scope.

### Relation to ADR-024

ADR-024 left the `SDD_*` environment variables and the `sdd-validation.yml`
workflow filename unchanged as compatibility-sensitive identifiers. This
decision changes exactly two of them, the workspace-root override and the ask
entrypoint, because the hook and the CLI disagree on them. The remaining `SDD_*`
names keep ADR-024's position until a separate RFC (M006).

## Consequences

- **Breaking:** retired names and markers are rejected rather than interpreted.
  Existing workspaces with legacy or stale adapters must regenerate. This
  requires an RFC and a CHANGELOG breaking entry (M006) before it ships.
- A new release is required: `v1.0.17` fixes POSIX only, and the cross-shell
  launcher is unreleased. The global install must be upgraded and regenerated
  from afterwards.
- `hook status` becomes a gate-quality signal (non-zero exit) instead of an
  informational printout.
- Copilot CLI context injection and Codex re-trust behavior remain observed
  limitations until tests settle them.
- No compatibility branch is left behind; rollback is a release revert.

## Open points

- Whether Copilot CLI consumes `additionalContext` for the PascalCase
  `UserPromptSubmit` form (not documented).
- Whether Codex's documented hash-based re-review applies exactly as written to the
  managed `config.toml` block after a regeneration (documented; observation pending).
- Whether one Copilot hook entry can carry both per-OS key sets.
- Whether the Python launcher runs under `cmd.exe` and PowerShell 5.1.
- Whether the 39 unreleased commits after `v1.0.17` change the hook further.

The first four are tracked as validation items V-01 to V-03 (the Codex and Copilot
questions as V-02 and V-03, the Windows shells as V-01), and the Devin questions below
as V-04, in `.analysis/pending/prompt-submit-hook-platform-validation.md` (a
workspace-local file; the results are folded into this ADR when they exist).

- Whether Devin CLI merges one hook registered in `.devin/hooks.v1.json` and in
  `.claude/settings.json`, which directory and shell run it, and whether it asks for
  trust.

## Implementation status (2026-10-12)

Implemented and verified in the source tree (unit and integration suites green):

| Decision | State |
|---|---|
| 1 Retired input rejected | Done: pre-rebrand hook reference, unmanaged Codex block and `sdd-commands.mdc` rejected or removed |
| 2 `hook status` from the real target and digest | Done: `legacy`, `broken`, `stale` states, exit 1 when unhealthy |
| 3 Never silent | Done: named reasons on stderr, `DEGRADED` notice for real failures, platform timeouts above the hook's |
| 4 One environment contract | Done (RFC-019, accepted 2026-10-12); breaking, ships in v1.0.18 |
| 5 Stale build not deployed | Done: `deploy_to_root` refuses a stale `final-template` |
| 6 Executable verified by behavior | Done: the CLI must echo `entrypoint : hook` (`cli_contract_mismatch`) and report the workspace fingerprint; version list, probe and cache, `.venv` search, `cwd` fallback and the fingerprint alias removed |
| 7 Merge fails closed | Done for the hook adapters and the Claude and Gemini seeds |
| 8 Launcher without OS encoding | Done for the tracked Copilot file (`bash`, `powershell`, `command`); CI job `Hook Launcher Gate` runs every generated adapter under the runner's shells (non-blocking on `windows-latest`); a developer machine is untested |
| 9, 10 Copilot and Codex limits | Done as stated notices in `hook status` and generation output; the Codex re-review rule is settled by the official documentation (hash of the exact definition, `/hooks`), observation pending |
| 11 `bootstrap-fallback` removed | Done; a missing template base raises |
| 12 Tracked copies under `docs/` | Done |
| 13 Executor check for side quests | Not a repository change; a Strategist defect (outside this repository) |
| 14 Devin CLI | Done in source: adapter, one-registration rule, `hook status`, validator, notice; the product behavior is unobserved (V-04) |

Not done: the Windows run of the launcher (CI evidence pending); the observed Codex
re-trust, Copilot per-OS key and Devin behavior. RFC-019 was accepted on 2026-10-12
(M006). The release that carries the cross-shell launcher and the environment contract is prepared
as `v1.0.18` (`v1.0.17` fixes POSIX only and still reads `SDD_*`); the tag is pending.

## Verification state

Source-tree behavior is covered by tests; `v1.0.18` is prepared but not tagged. Until
a CLI that carries this change is installed (the global CLI is `1.0.17`), the deployed
hook is the `1.0.17` template, not this tree's.

## Links

- Runbook: [dead-prompt-submit-hook-adapter.md](../runbooks/dead-prompt-submit-hook-adapter.md)
- [ADR-024-providence-cicd-brand-alignment.md](ADR-024-providence-cicd-brand-alignment.md)
- [ADR-022-managed-block-seed-convention.md](ADR-022-managed-block-seed-convention.md)
