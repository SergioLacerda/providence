# Client Bootstrap PATH Shadowing

Verification state: documented

## Symptoms

- A command works with `uv run providence ...` but fails as plain `providence ...`.
- Local development appears to use an older CLI behavior.
- A global `providence-cli` install shadows the repository's `.venv` executable.
- Bootstrap or setup commands fail with unexpected command-shape errors.

## Diagnosis

1. In this repository, prefer the workspace command:

   ```bash
   uv run providence --help
   ```

2. Compare it with the global executable:

   ```bash
   which providence
   providence --help
   ```

3. Check whether `providence` was installed globally with `uv tool install` or `pipx`.
4. If a client project is involved, confirm it is using a released Providence CLI version,
   not default-branch HEAD.

## Resolution Steps

1. For this repository, run commands as:

   ```bash
   uv run providence <command>
   ```

2. If global shadowing keeps causing confusion, remove the global tool:

   ```bash
   uv tool uninstall providence-cli
   ```

3. For client onboarding, install from a release wheelhouse or tag-pinned git URL.
4. Re-run the original failing bootstrap command with the intended executable.

## Rollback

1. Reinstall the global CLI only if it is needed for adopter workflows.
2. Pin it to a known release tag.
3. Keep repository development commands on `uv run providence`.

## Post-Incident

- Add the failing command shape and the executable path to the failure ledger if
  this caused a real support incident.
- Update onboarding docs if a new shadowing pattern appears.

## Evidence To Attach

- `which providence`
- `providence --help`
- `uv run providence --help`
- installed package version or `uv tool list`

## Sources

- `docs/guides/ONBOARDING.md`
- `docs/guides/CLIENT_ONBOARDING.md`
- `docs/guides/CONVERGENCE.md`
