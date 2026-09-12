# CI Known Failure Triage

Verification state: incident-backed

Use this runbook before re-diagnosing a repeated GitHub Actions failure. The
same CI thread produced three distinct failure classes across three separate
jobs; each was mistaken for a fresh incident until the failing ref, branch
tips, and error text were compared against known signatures. Check the
matrix below first.

## Symptoms

- `npm ci` fails in `security / npm Audit (apps/landing)` or `docs-quality`
  with an `ERESOLVE` conflict naming `@astrojs/check@0.9.10` and
  `typescript@7.0.2`.
- `Environment Boundary Preflight` (or another job bootstrapping `uv`) fails
  in the `astral-sh/setup-uv@v9` step with `Unexpected input(s) 'cache'` or a
  timeout resolving `uv.ndjson` for `version: "latest"`.
- `Release Git Install Smoke (windows-latest)` fails with an "ambiguous
  user/pass authority" URL-parsing error against a `git+file:///D:/...@<sha>`
  local install URL, or with a `uv-resolver` panic after `uv` reports
  `Updating file:///D:/... (HEAD)`.

## Diagnosis

1. Identify the failing job name and the workflow file that defines it.
2. Before assuming a code defect, compare the failing ref against
   `origin/main`, `origin/develop`, and local `HEAD`:

   ```bash
   git show origin/main:apps/landing/package.json | rg -n 'typescript|@astrojs/check'
   git show origin/develop:apps/landing/package.json | rg -n 'typescript|@astrojs/check'
   ```

   A fix already present on another branch or on local `HEAD` but not on the
   failing ref is not a new defect — it is a promotion/merge gap.
3. Match the error text against the known signature matrix:

   | Signature | Root cause | Fast check | Durable prevention |
   |---|---|---|---|
   | `ERESOLVE`, `@astrojs/check@0.9.10`, `typescript@7.0.2` | The failing ref still requests TypeScript 7 while `@astrojs/check` only supports `^5 \|\| ^6` | Compare `origin/main`, `origin/develop`, and local `apps/landing/package.json` | Keep TypeScript pinned to `^6.0.3` in `apps/landing`; keep the Dependabot semver-major ignore rule (see [ADR-018](../adr/ADR-018-dependabot-typescript-major-ignore.md)) until Astro tooling supports TypeScript 7 |
   | `Unexpected input(s) 'cache'`, `uv.ndjson` timeout | `astral-sh/setup-uv@v9` received the obsolete `cache` input and resolved `version: "latest"` through a live manifest fetch | Scan the workflow's `setup-uv` step block for `cache:` and `version: "latest"` | Pin `version` to a known-good release (e.g. `0.11.9`) and use `enable-cache: true` instead of `cache:` |
   | "ambiguous user/pass authority", `uv-resolver` panic, `git+file:///D:/...@sha` | On Windows, `uv` can re-parse local `git+file:///D:/...` installs with a resolved `@<sha>` as URL authority instead of a git ref | Inspect the release source-install smoke step for any `git+file://` URL | Install the checkout package path directly with `uv tool install ./packages/interfaces/providence_cli`; do not add sibling packages via `--with-editable`, because the workspace already resolves them locally |

   If the error text does not match any row, do not assume one of these
   fixes applies — follow [Escalation](#escalation).

## Resolution Steps

### TypeScript / `@astrojs/check` peer mismatch

1. Confirm `apps/landing/package.json` pins `typescript` to `^6.0.3` on the
   ref actually being built (per step 2 above).
2. If the failing ref is behind, promote/merge the already-fixed ref rather
   than re-patching `package.json` locally.
3. Re-run:

   ```bash
   npm ci
   ```

### `setup-uv` invalid input / `latest` timeout

1. Check every `astral-sh/setup-uv@v9` block in the affected workflow for
   `cache:` (invalid input) or `version: "latest"`.
2. Replace with a pinned `version` and `enable-cache: true`.
3. Validate workflow YAML parses:

   ```bash
   python3 -c 'import pathlib, yaml; [yaml.safe_load(p.read_text()) for p in pathlib.Path(".github/workflows").glob("*.yml")]; print("workflow yaml ok")'
   ```

### Windows local source-install URL

1. Locate the release workflow's source-install smoke step.
2. Remove any local `git+file://` URL from that step. Even without an explicit
   `@<ref>` suffix, `uv` may resolve `HEAD` and re-parse the Windows drive-letter
   URL with an ambiguous authority.
3. Install the CLI package path directly and let `uv` resolve workspace-local
   sibling packages once:

   ```bash
   uv tool install ./packages/interfaces/providence_cli
   ```

   Do not add the sibling packages with `--with-editable`; that creates
   conflicting URL sources such as `file:///.../providence_integration` and
   `file:///.../providence_integration (editable)`.

3. Re-run the targeted policy test:

   ```bash
   UV_CACHE_DIR=/tmp/uv-cache uv run python -m pytest -q -o addopts='' tests/unit/ci/test_release_workflow_policy.py
   ```

### After any of the above

```bash
uv run providence governance validate
```

## Rollback

1. Revert the workflow or dependency edit that did not clear the failure.
2. Re-run the branch/ref comparison in [Diagnosis](#diagnosis) — a rollback
   is often unnecessary if the actual fix already exists on another ref.
3. Do not re-apply a prevention fix (Dependabot ignore, `setup-uv` pin, URL
   shape) that is already present on the ref being built.

## Post-Incident

- Keep the TypeScript Dependabot ignore rule in place; only remove it after
  confirming live that `@astrojs/check` supports TypeScript 7
  ([ADR-018](../adr/ADR-018-dependabot-typescript-major-ignore.md)).
- These three preventions are documented here but not yet enforced by tests
  or guards. Tracked as follow-up work, not covered by this runbook:
  - a workflow policy test for `setup-uv@v9` version/cache input shape;
  - a dependency-compatibility guard for TypeScript major vs. the
    `@astrojs/check` peer range;
  - a branch-state triage checklist in PR/workflow docs.

## Evidence To Attach

- Failing job name and workflow file.
- Output of the `origin/main` / `origin/develop` / local `HEAD` comparison.
- Relevant error text from the job log.
- Output of the validation command(s) run for the matched signature.

## Escalation

- If the error text does not match any row in the known signature matrix,
  treat it as a new failure and diagnose fully — do not force-fit it to one
  of these three cases.
- If a matched signature's resolution steps do not clear the failure,
  escalate instead of repeating the same fix; the release and Windows
  install-smoke paths in particular can affect shipped release artifacts.

## Sources

- [ADR-018: Dependabot TypeScript Major Ignore](../adr/ADR-018-dependabot-typescript-major-ignore.md)
- `.github/dependabot.yml`
- `.github/workflows/docs.yml`
- `.github/workflows/reusable-security.yml`
- `.github/workflows/health.yml`
- `.github/workflows/release.yml`
- `.github/workflows/release-dry-run.yml`
- `tests/unit/ci/test_release_workflow_policy.py`
