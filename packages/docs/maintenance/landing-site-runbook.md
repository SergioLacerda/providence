# Landing / Site Maintenance Runbook

This is the operational reference for maintaining the published site: the Astro
landing page, the MkDocs documentation corpus, and the Selector. It exists so an
agent (or a human) picking up a maintenance task here does not have to re-derive the
architecture or re-read the `.analysis/` mission history that produced these
decisions. Where a decision was made elsewhere, this page links to it rather than
re-explaining it.

## 1. Architecture Map

Three independently-built pieces compose into one shared publication root,
`build/site/` (see the accepted ADR,
`.analysis/archived/selector-landing-mkdocs-refinement-20260702-adr.md` — see §7 for
why this is plain text, not a link):

| Piece | Source | Publishes to | Key files |
|---|---|---|---|
| Landing app | `apps/landing/` (Astro 7 + React 19) | `/` | `astro.config.mjs` (`base: '/providence/'`), `src/pages/index.astro`, `src/components/Landing.tsx`, `src/lib/i18n.ts`, `src/layouts/BaseLayout.astro` |
| Docs | `docs/` (MkDocs) | `/docs/` | `mkdocs.yml` (`site_dir: build/site/docs`), `docs/README.md` (navigation index) |
| Selector | compiled by `selector_compiler_cli.py` | `/selector/` | `packages/interfaces/providence_wizard/src/providence_wizard/orchestration/wizard/selector_compiler_cli.py` |

`apps/landing/` currently has no `README.md` of its own — this runbook is the closest
thing to one; the landing app's build/lint/test commands are covered in §2.

## 2. Local Development Loop

All commands are `Makefile` targets (`Makefile:180-193` at time of writing):

| Command | What it does |
|---|---|
| `make docs-build` | Full build: Astro build (`build-web`) → `mkdocs build --strict` → Selector compiler CLI into `build/site/selector` |
| `make docs-serve` | Depends on `docs-build`, then guards and serves locally (see below) |
| `make docs-link-check` / `make docs-link-fix` | Link validation/fix via `tools/maintenance/make_tasks.py` |
| `make install-web` / `build-web` / `lint-web` (`astro check`) / `test-web` / `cover-web` | Astro app-specific install/build/lint/test/coverage |

`make docs-serve` mounts `build/site` under `build/serve-root/providence` (a symlink)
and serves at **`http://localhost:8000/providence/`**, not the server root — this
matches the Astro app's `base: '/providence/'` config used for GitHub Pages sub-path
deployment, so local links/assets resolve the same way they do in production.

Before serving, `docs-serve` checks `build/site/selector/index.html` exists and fails
loudly with an actionable message if it doesn't, instead of serving a broken build that
404s at the browser. This guard exists specifically because of the selector-404 failure
mode described in §5.

## 3. CI / Deploy Pipeline

`.github/workflows/docs.yml` ("Documentation Quality & Publish"):

1. Installs Node dependencies for `apps/landing`, lints and tests it.
2. Runs `make docs-build` — the same target used locally (no separate CI-only build
   logic; this was previously a source of drift, see §7).
3. Validates the docs search index (`providence_pages.selector.DocumentIndexer`).
4. Gzip-compresses assets.
5. Deploys via `actions/deploy-pages`.

Deploy is gated on `vars.ENABLE_GITHUB_PAGES == 'true'` **and** push to `main`.

## 4. Established i18n Conventions

These are already-made architectural decisions — don't re-derive them, read the source:

- **Docs i18n**: MkDocs via the `mkdocs-static-i18n` plugin — English is the default
  locale, Portuguese via a locale suffix (`docs/pt/...`). See
  `.analysis/done/2026-06-15-i18n-mkdocs-selector-design.md`.
- **Selector i18n**: a runtime `?lang=pt` JS query param — no compiler-side i18n
  branching. Build order was inverted specifically to eliminate an intermediate
  `docs/selector/` directory (same design doc above).
- **Landing app i18n**: `apps/landing/src/lib/i18n.ts` holds a bilingual
  `LANDING_CONTENT` dictionary consumed by `Landing.tsx` and related components.

## 5. Known Failure Modes

### Selector 404

- **Symptom**: visiting `/selector/` (or the landing page's link to it) 404s.
- **Root cause**: `build/site/selector/` wasn't produced — usually an incomplete or
  skipped `make docs-build` run. The landing page's link-out to
  `${BASE_URL}selector/` (`Landing.tsx`) is correct by design — it's a deliberate
  link-out to a separately built page, not an embedded preview (per the 2026-07-02
  ADR linked in §1).
- **Status**: **resolved**. `make docs-serve` now fails loudly (see §2) instead of
  serving a broken build.
- **Evidence**: `.analysis/done/20260724T132403Z-landing-selector-docs-link/analysis.md`
  (confidence 0.9).

### pt Sitemap 404 (`docs/pt/sitemap.xml`)

- **Symptom**: `docs/pt/sitemap.xml` (and `.gz`) don't exist; only the default-locale
  `docs/sitemap.xml` does.
- **Root cause**: confirmed upstream `mkdocs-static-i18n` behavior — it replicates the
  page tree per locale but not MkDocs's root-only special files. Not a repo defect.
- **Status**: **expected, not a bug**. No in-repo consumer needs a per-locale sitemap
  today. Documented inline at `mkdocs.yml:46-50`. A per-locale sitemap generator was
  considered and explicitly deferred, not built.

## 6. Common-Task Playbook

| Trigger | Steps | Verify with |
|---|---|---|
| Add or edit a docs page | Create/edit under `docs/`, following the existing nav structure in `mkdocs.yml` | `make docs-build` (strict mode catches broken nav refs), then `make docs-link-check` |
| Add or update landing-page copy (i18n) | Edit the `LANDING_CONTENT` dict in `apps/landing/src/lib/i18n.ts` for both `en`/`pt` keys | `make lint-web` and `make test-web` |
| Investigate a broken link or 404 | Run `make docs-build` locally and read the full console output for the failing step (Astro / MkDocs / Selector) before assuming a source bug — most historical link issues traced to an incomplete build (§5), not a defect | `make docs-link-check` |
| `docs-serve` guard fires (`build/site/selector/index.html` missing) | Re-run `make docs-build` in full — don't skip straight to `docs-serve` | Guard passes silently on the next `make docs-serve` |

## 7. References

`.analysis/` is gitignored and sits outside the MkDocs `docs/` source tree, so it
cannot be linked with a resolvable Markdown link from a strict-mode MkDocs page
(`mkdocs build --strict` treats any relative link as one it must resolve inside
`docs/`, and fails the build otherwise). The paths below are plain text — copy them
into your editor or `cat` them directly:

- `.analysis/archived/selector-landing-mkdocs-refinement-20260702-adr.md` — publication boundary ADR (Astro owns `/`, MkDocs under `/docs/`, Selector under `/selector/`)
- `.analysis/done/2026-06-15-i18n-mkdocs-selector-design.md` — i18n architecture
- `.analysis/done/2026-07-02-unify-web-publish-pipeline-design.md` — CI/Makefile build unification
- `.analysis/done/20260724T132403Z-landing-selector-docs-link/analysis.md` — selector-404 / pt-sitemap diagnostic
