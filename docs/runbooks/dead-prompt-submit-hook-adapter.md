# Dead Prompt-Submit Hook Adapter

Verification state: documented

The prompt-submit hook injects governance context into agent sessions. When an
adapter points at a target that does not exist, or the executable that runs the
hook is stale, the hook does nothing and nothing says so. Use this runbook to find
and repair that state. The decisions behind it are in
[ADR-025](../adr/ADR-025-prompt-submit-hook-hardening.md).

`.providence/` and the agent adapter files are **generated output**. Regenerate them;
do not hand-edit them as authored source.

## Symptoms

- Agent replies carry no `PROVIDENCE GOVERNANCE ACTIVE` header although the workspace
  is governed.
- `providence governance hook status` prints `configured (stale)`, or `configured`
  for an adapter whose command points outside the workspace.
- An adapter command contains `generated/client/compiled/`, or the shape
  `sh -c 'hook=$1; if [ -f "$hook" ]; then exec python3 "$hook"; fi; exit 0' sh /…`.
- `which -a providence` resolves to a version older than the repository source.
- The hook reports a `reason=` on stderr or a `PROVIDENCE GOVERNANCE DEGRADED` notice.
  `cli_contract_mismatch` means the `providence` on `PATH` does not echo
  `entrypoint : hook` (it predates the environment contract, RFC-019: 1.0.17 and older
  report `explicit_command`); `cli_fingerprint_mismatch` means its context belongs to
  another governance fingerprint; `cli_not_found` means `providence` is not on `PATH`
  (the workspace `.venv` is not searched). Upgrade to `providence-cli` 1.0.18 or newer,
  the release that carries RFC-019.

## Diagnosis

Read-only checks first.

1. Which executable runs, and which version:

   ```bash
   which -a providence
   providence --version
   uv tool list
   ```

   Versions `1.0.14` to `1.0.16` generate the dead absolute-path command. `1.0.17`
   generates a POSIX `sh` launcher and repairs Linux and macOS only.

2. What each adapter actually runs:

   ```bash
   grep -n "prompt-submit" .claude/settings.json .codex/config.toml \
     .gemini/settings.json .github/hooks/providence-prompt-submit.json \
     .devin/hooks.v1.json
   ```

3. Whether the central hook exists and where:

   ```bash
   test -f .providence/runtime/hooks/prompt-submit.py && echo present || echo missing
   ```

   If an adapter command embeds an absolute path, test that exact path with `test -f`.

4. Whether the hook was disabled on purpose:

   ```bash
   providence governance hook status
   ls .providence/runtime/hook-disabled
   ```

5. Platform-specific causes:
   - **Codex** trusts a project hook by the hash of its exact definition and only
     when the project `.codex/` layer is trusted. An untrusted or changed definition
     is skipped without an error; Codex prints a startup warning pointing at `/hooks`.
   - **Devin CLI** loads `.claude/settings.json` hooks by default as well as
     `.devin/hooks.v1.json`; the generator writes only one of them, and
     `providence governance hook status` reports `broken (registered twice ...)` when
     both carry the hook. Its working directory and Windows shell are not documented,
     so the launcher reads `DEVIN_PROJECT_DIR`.
   - **Copilot CLI** drops the output of config-file `userPromptSubmitted` hooks. Whether
     `additionalContext` is consumed for the PascalCase `UserPromptSubmit` form is not
     documented, so injection there is not guaranteed.

## Resolution Steps

1. Back up the adapters you are about to regenerate (they are not tracked by git):

   ```bash
   mkdir -p /tmp/hook-adapters.bak
   cp -p .claude/settings.json .codex/config.toml .gemini/settings.json /tmp/hook-adapters.bak/ 2>/dev/null
   ```

2. Upgrade the executable. Do this before regenerating, otherwise the same stale
   generator writes the same dead command:

   ```bash
   uv tool upgrade providence-cli
   providence --version
   ```

   Until a release contains the cross-shell launcher, a Windows machine needs the
   repository build instead of `1.0.17`.

3. Regenerate the adapters and the deployed hook:

   ```bash
   providence governance generate
   ```

4. Verify:

   ```bash
   providence governance hook status
   ```

   Expect `configured` for every platform, no `stale`, `broken` or `legacy` line, and
   exit status 0 (the command exits 1 when any adapter is broken, stale or legacy).
   Then send one prompt per platform and look for the activation header.

5. Codex only: regeneration changes the definition's hash, so open `/hooks`, review
   the regenerated hook and trust it; until then Codex skips it.

## Rollback

- Restore the adapter files copied in step 1 of Resolution Steps.
- Reinstall the previous executable with `uv tool install providence-cli==<version>`.
- To stop the hook without removing it: `providence governance hook disable`; undo
  with `providence governance hook enable`.

## Post-Incident

- Record the finding in the [Failure Ledger](../incidents/FAILURE_LEDGER.md) with the
  version that generated the adapter.
- Check whether the repository build was fresher than the global executable
  (this was the root cause the first time).
- If the symptom recurs after upgrading, compare the deployed hook with the template
  constant `PROMPT_SUBMIT_HOOK_SCRIPT` in `prompt_submit_hook_script.py`; a different
  digest means a stale deployment.

## Evidence To Attach

- Output of `which -a providence`, `providence --version` and `uv tool list`.
- The `prompt-submit` lines of each adapter file.
- The output of `providence governance hook status` before and after.
- Which agent platforms were affected and whether the activation header appeared.

## Escalation

This procedure affects governance artifacts and the context agents receive. Escalate
to a maintainer if `hook status` stays stale after a clean regeneration, if more than
one platform is affected after the upgrade, or if the adapters must be edited by hand.

## Sources

- [ADR-025: Prompt-Submit Hook Hardening](../adr/ADR-025-prompt-submit-hook-hardening.md)
- [Governance Runtime Drift](governance-runtime-drift.md)
- [Client Bootstrap PATH Shadowing](client-bootstrap-path-shadowing.md)
- [Runbook Authoring Standard](authoring-standard.md)
- Codex hooks: `https://learn.chatgpt.com/docs/hooks`
- Gemini CLI hooks reference: `https://geminicli.com/docs/hooks/reference/`
- Copilot hooks configuration: `https://docs.github.com/en/copilot/reference/hooks-configuration`
