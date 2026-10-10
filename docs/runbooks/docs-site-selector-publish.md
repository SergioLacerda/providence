# Docs Site and Selector Publish

Verification state: active

## Scope

The repository publishes MkDocs documentation and generates the machine-readable
Selector artifact. The landing and Selector presentation pages are supplied by
pin-verified ILUSIONISTA releases during `make docs-build`.

## Symptoms

- `/selector/` is missing locally or after publishing;
- `build/site/selector/data.json` is absent or invalid;
- CI validates MkDocs but the composed site is incomplete;
- `make docs-build` refuses to publish because an ILUSIONISTA pin is disabled
  or cannot be verified.

## Diagnosis

1. Run the complete build:

   ```bash
   make docs-build
   ```

2. Check the protected Selector outputs:

   ```bash
   test -f build/site/selector/index.html
   test -f build/site/selector/data.json
   test -f build/site/selector/docs.index.json
   ```

3. If only governance data is needed, run:

   ```bash
   make selector-artifact
   ```

   This command must not create HTML, CSS, or JavaScript page assets.

## Resolution

1. Do not hand-build a local landing or Selector page.
2. Fix the reported ILUSIONISTA archive, checksum, required-entry, or path-
   safety failure.
3. Confirm the Selector compiler can still produce `data.json` from `.providence`
   sources or its canonical-doc fallback.
4. Rerun `make docs-build` and validate the generated docs index.
5. For a live deployment, record external release and Pages evidence separately
   from these local deterministic checks.

## Rollback

There is no local presentation rollback path. If the pinned ILUSIONISTA release
is not usable, block publication and use `make selector-artifact` for artifact
diagnostics until a verified release is available.

## Evidence To Attach

- `make docs-build` output;
- `build/site/selector/data.json` validation;
- `build/site/selector/docs.index.json` validation;
- `build/site/.compressed/manifest.json` when compression runs;
- the ILUSIONISTA tag, archive, and checksum evidence;
- authorized live deployment evidence, if applicable.

## Sources

- `docs/maintenance/landing-site-runbook.md`
- `docs/guides/FRONTEND_SELECTOR.md`
- `docs/guides/GITHUB_PAGES_PUBLISH_CHECKLIST.md`
