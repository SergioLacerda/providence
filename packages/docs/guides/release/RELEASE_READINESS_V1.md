# Release Readiness v1.0 Checklist

Approved: yes
Decision-Owner: Sergio Lacerda
Decision-Date: 2026-05-24
Target-Version: v1.0.0

## Pre-Release Criteria

- [x] SemVer tag validation gate exists (`release.yml`, `release-dry-run.yml`)
- [x] Changelog entry validation gate exists
- [x] Unit/integration release-critical tests run in release workflows
- [x] Strict golden policy gate runs in release workflows
- [x] Version/tag consistency check is enforced
- [x] Build + artifact upload stage is defined
- [x] Windows and Linux install smoke test runs against `dist/` artifacts
      before publish (`release-install-smoke` job)
- [x] SBOM generation is defined
- [x] Artifact signing step is defined and blocking (release fails if
      signing fails)
- [x] Provenance/attestation step is defined

## Gate Points

1. `release-dry-run.yml` validates release candidate before publish,
   including the Windows/Linux install smoke lane
2. `release.yml` blocks release on validate/build/install-smoke failures
3. strict golden policy is required in both release paths
4. `release.yml` install smoke installs `providence-cli` from `dist/` only
   (`--no-index --find-links dist`) and runs `sdd --help`,
   `providence install --help`, and `providence wizard --list`

## Rollback Contract

### Trigger Conditions

Rollback is recommended when one or more conditions are true after release:

- critical regression in release-critical tests (post-release verification)
- signing/provenance verification fails downstream
- operational severity exceeds accepted threshold

### Rollback Command Path

1. Identify last known good tag in GitHub Releases.
2. Re-deploy previous artifact set from signed release assets.
3. Open incident entry in `docs/incidents/FAILURE_LEDGER.md`.

## Branch Protection Prerequisite (Manual)

`release-dry-run.yml` runs automatically on every push to `main` (in addition
to its manual `workflow_dispatch` form), so that the full release build is
validated continuously instead of only being caught the first time someone
pushes a real tag. This is only an effective gate if it is also required to
pass before merging to `main`.

This must be configured once, manually, in the GitHub repository settings —
it is not something a workflow file can enforce on its own:

- Settings → Branches → branch protection rule for `main` → require status
  checks to pass before merging → add the `dry-run` job (or, after the
  `dry-run-build` job exists, both `dry-run` and `dry-run-build`) from
  `release-dry-run.yml`.
4. Record postmortem and update playbooks in `docs/incidents/PLAYBOOKS.md`.

## Pre-Build Dependency Check (Manual)

Dependabot (`.github/dependabot.yml`) targets `develop`. Before cutting a build or
promoting `develop` to `main` for release, check for outstanding dependency PRs so
they don't silently ride along unreviewed:

```bash
gh pr list --base develop --label dependencies --state open
```

If this returns open PRs, decide per-PR whether to merge them into `develop` first
or explicitly defer them — don't let a release proceed without an explicit decision
on each one.
