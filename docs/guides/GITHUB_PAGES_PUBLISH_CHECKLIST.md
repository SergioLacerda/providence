# GitHub Pages Publish Checklist

Use this checklist when docs workflows are green but the site was not updated.

## 1) Repository settings

1. GitHub repository has **Pages** enabled.
2. Pages source is set to **GitHub Actions**.
3. Repository variable `ENABLE_GITHUB_PAGES` is set to `true`.

## 2) Publication artifact model

The Pages artifact is built as a composed publication surface:

1. Pin-verified ILUSIONISTA owns the root landing surface at `/`.
2. MkDocs owns canonical technical documentation under `/docs/`.
3. Pin-verified ILUSIONISTA owns the Selector presentation at `/selector/`.
4. The local Selector compiler generates `selector/data.json`.

Use `make docs-build` for local publication verification because it builds the
composed site: verified ILUSIONISTA surfaces, strict MkDocs docs, and the
machine-readable Selector artifact.

## 3) Trigger conditions in `docs.yml`

Publish only runs when all conditions are true:

1. Event is `push`.
2. Branch is `main`.
3. `vars.ENABLE_GITHUB_PAGES == 'true'`.

Reference: `.github/workflows/docs.yml`.

## 4) Required file-change paths

The workflow triggers on changes in:

- `docs/**`
- `mkdocs.yml`
- `README.md`
- docs validation scripts under `tools/`
- `.github/workflows/docs.yml`

If your commit does not touch these paths, docs workflow will not run.

## 5) Fast local verification

```bash
make docs-build
```

If this fails locally, fix the affected publication surface before expecting
publish.

## 6) CI verification

In GitHub Actions:

1. `docs-quality` must pass.
2. `Upload Pages artifact` step must run (not skipped).
3. `deploy` job must run and succeed.

If `deploy` is skipped, the most common cause is `ENABLE_GITHUB_PAGES` not set to `true`.
