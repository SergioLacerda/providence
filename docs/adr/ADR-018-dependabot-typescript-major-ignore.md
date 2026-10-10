# ADR-018 - Block Dependabot typescript Major Bumps in apps/landing

> Historical and superseded: the local Astro landing application and its npm
> dependency surface were removed. Public presentation is now supplied by
> pin-verified ILUSIONISTA releases.

**Status:** Accepted
**Date:** 2026-07-30
**Deciders:** Sergio Lacerda
**Supersedes:** N/A
**Mission:** 20260730-dependabot-typescript-astro-conflict

---

## Context

Dependabot has repeatedly proposed major-version bumps of `typescript` in
`apps/landing`, breaking `npm ci` in CI
(`.github/workflows/docs.yml`, `.github/workflows/reusable-security.yml`)
with an `ERESOLVE` conflict: `@astrojs/check@0.9.10` declares a peer
dependency of `typescript@"^5.0.0 || ^6.0.0"`, which does not include
`typescript@7.x`.

This is not an isolated incident. Commit history shows the pattern
recurring at least four times: `d8a45a4` was a manual downgrade fix,
followed by further automated `typescript` bumps in `29c75f4`, `01e3606`,
and `4ae56cb`. The current Dependabot grouping
(`dev-dependencies-major` in `.github/dependabot.yml`) only bundles updates
that are available *simultaneously* — it does not model cross-package peer
dependency compatibility. Whenever a new `typescript` major is published
before a compatible `@astrojs/check` major exists, Dependabot proposes
`typescript` alone, landing outside the supported peer range.

## Decision

Add an `ignore` rule for `typescript` major-version updates to the
`apps/landing` npm entry in `.github/dependabot.yml`:

```yaml
ignore:
  - dependency-name: "typescript"
    update-types: ["version-update:semver-major"]
```

`typescript` continues to receive minor/patch updates within `^6.x` as
normal. The rule should be removed once `@astrojs/check` (or its
`@astrojs/language-server` / `@volar/kit` dependency chain) publishes
support for `typescript@7.x`.

### Alternatives considered

| Option | Why rejected |
|---|---|
| Group `typescript` with `@astrojs/check` in Dependabot | Does not fix the issue on its own — grouping only bundles updates that are available at the same time; if `@astrojs/check` has no compatible major yet, `typescript` is still proposed alone |
| Keep the status quo (reactive manual fix) | Already failed repeatedly (4+ occurrences); depends on someone noticing broken CI |
| Pin `typescript` to an exact version (no `^`) | Also blocks legitimate minor/patch updates (e.g. security fixes) — broader than necessary |

## Consequences

- CI stops breaking from this specific cause until `@astrojs/check` ships
  `typescript@7.x` support.
- `typescript` in `apps/landing` is temporarily capped at `^6.x` — acceptable,
  since the tooling dependency (`@astrojs/check`) is what actually sets the
  compatibility ceiling, not an arbitrary project choice.
- Follow-up (outside this decision's scope): periodically check whether
  `@astrojs/check` has added `typescript@7.x` support
  (`npm view @astrojs/check versions --json` or the Astro changelog) and
  remove the `ignore` rule once it has.
- Applying the `.github/dependabot.yml` change itself is a separate,
  explicitly authorized implementation step — this ADR records the decision,
  it does not itself constitute the config edit.
