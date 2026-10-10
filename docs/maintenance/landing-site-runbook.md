# Published Site Maintenance Runbook

This is the operational reference for maintaining the published site: the
pin-verified ILUSIONISTA landing and Selector surfaces plus the MkDocs
documentation corpus. The local repository owns documentation and generated
machine-readable artifacts; it does not contain presentation-page sources.

## 1. Architecture Map

The build composes one shared publication root, `build/site/`:

| Piece | Source/owner | Publishes to | Key contract |
|---|---|---|---|
| Landing surface | Pin-verified ILUSIONISTA release | `/` | `IllusionistSurfaceComposer` verifies archive, checksum, paths, and required entries |
| Docs | `docs/` (MkDocs) | `/docs/` | `mkdocs.yml` writes to `build/site/docs` |
| Selector surface | Pin-verified ILUSIONISTA release | `/selector/` | External HTML/JS/CSS is composed only after verification |
| Selector artifact | `selector_compiler_cli.py` | `build/site/selector/data.json` | `.providence` sources with canonical-doc fallback |

The local Selector compiler never owns HTML, JavaScript, or CSS. It cannot
recreate either presentation surface.

## 2. Local Development Loop

| Command | What it does |
|---|---|
| `make selector-artifact` | Generates `build/site/selector/data.json` without a presentation build |
| `make docs-build` | Verifies both ILUSIONISTA archives, builds strict MkDocs, and generates the Selector data artifact |
| `make docs-serve` | Runs `docs-build`, verifies the externally composed Selector entrypoint, and serves `build/site` at `http://localhost:8000/providence/` |
| `make docs-link-check` / `make docs-link-fix` | Validates or fixes documentation links |

`make docs-build` fails closed when ILUSIONISTA is disabled or its pins cannot
be verified. It does not resurrect a local fallback. Use
`make selector-artifact` when only the machine-readable artifact is needed.

## 3. CI / Deploy Pipeline

`.github/workflows/docs.yml`:

1. Runs `make docs-build`, using the same path as local development.
2. Generates and validates `build/site/selector/docs.index.json`.
3. Compresses HTML, CSS, JavaScript, SVG, and JSON files and writes
   `build/site/.compressed/manifest.json`.
4. Uploads the Pages artifact and deploys via `actions/deploy-pages` when
   Pages is enabled on `main`.

The protected generated outputs are:

- `build/site/selector/data.json` — Selector governance payload;
- `build/site/selector/docs.index.json` — documentation search index;
- `build/site/.compressed/manifest.json` — compression evidence;
- the governance artifacts generated under `.providence/compiled/` by the
  existing governance pipeline.

## 4. Established i18n Conventions

- **Docs i18n**: MkDocs via `mkdocs-static-i18n` — English is the default
  locale and Portuguese uses the existing locale suffixes.
- **Selector i18n**: the externally owned surface handles `?lang=pt`; the
  artifact compiler does not branch on presentation language.
- **Landing and Selector presentation**: content changes are made in a new
  versioned ILUSIONISTA release and its pinned coordinates, not in this repo.

## 5. Known Failure Modes

### Selector 404

- **Symptom**: `/selector/` is absent locally or after publishing.
- **Root cause**: `make docs-build` did not complete, or the pinned ILUSIONISTA
  Selector archive was unavailable, invalid, or structurally incomplete.
- **Diagnosis**: inspect the `SurfaceError`, then verify
  `build/site/selector/index.html` and `build/site/selector/data.json`.
- **Resolution**: fix the release coordinates or archive contract and rerun
  `make docs-build`; do not add local page assets.

### Artifact-only generation

- **Use**: `make selector-artifact`.
- **Expected output**: `build/site/selector/data.json` only.
- **Validation**: parse the JSON and verify the governed item/dependency
  contract with the Selector compiler tests.

### Portuguese sitemap 404

The existing `mkdocs-static-i18n` behavior remains expected: root-only special
files such as the sitemap are generated for the default locale only.

## 6. Common-Task Playbook

| Trigger | Steps | Verify with |
|---|---|---|
| Add or edit a docs page | Edit under `docs/` and follow `mkdocs.yml` navigation | `make docs-build`, then `make docs-link-check` |
| Change landing or Selector presentation | Publish a new pin-verified ILUSIONISTA release and update its pinned coordinates | `make docs-build` plus authorized live deployment evidence |
| Change Selector governance data | Update governed sources, then run the artifact compiler tests | `make selector-artifact` and targeted Selector tests |
| `docs-serve` guard fires | Rerun the complete `make docs-build`; inspect ILUSIONISTA verification first | `build/site/selector/index.html` and `data.json` |

## 7. Historical References

`.analysis/` is gitignored and intentionally retained as historical evidence.
The archived publication-boundary analysis describes the earlier local-page
ownership model; the active contract in this runbook supersedes that ownership
while preserving the audit trail.
