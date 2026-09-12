# Standalone Compiler Release Asset Contract

Standalone `providence-cli` installs (no local repo checkout, no `sdd-compile` on
`PATH`) resolve the Go `sdd-compile` binary from the wheel-packaged native
assets first, then fall back to the GitHub Release matching the installed
`providence-cli` version. This document is the contract that release automation and
`CompilerRunner` both rely on.

## Required assets

Every tagged release (`vX.Y.Z` or `VX.Y.Z`) must expose these six files
through the GitHub Release **assets** API (not just the release UI):

```text
sdd-compile-linux-amd64
sdd-compile-linux-arm64
sdd-compile-darwin-amd64
sdd-compile-darwin-arm64
sdd-compile-windows-amd64.exe
SHA256SUMS
```

`SHA256SUMS` must list each compiler binary by its **bare filename** (no
`dist/` prefix, no path separators):

```text
<sha256>  sdd-compile-linux-amd64
<sha256>  sdd-compile-linux-arm64
<sha256>  sdd-compile-darwin-amd64
<sha256>  sdd-compile-darwin-arm64
<sha256>  sdd-compile-windows-amd64.exe
```

GitHub's automatic `Source code (zip)` / `Source code (tar.gz)` links are
**not** release assets — they never appear in the Releases API `assets`
array, and `CompilerRunner` cannot use them.

## Enforcement points

`tools/release/validate_release_assets.py` is the single source of truth
for the asset matrix and `SHA256SUMS` shape (see
`tests/unit/tools/test_validate_release_assets.py`). It is wired into
`.github/workflows/release.yml` at three points:

1. **Pre-publication staging gate** (`release` job, "Verify release assets
   are staged") — runs the validator against `dist/` before anything is
   published. Fails the build if any asset or checksum entry is missing.
2. **Standalone install smoke** (`release-install-smoke` job) — installs
   `providence-cli` from `dist/` only (no PyPI fallback), does not set
   `SDD_COMPILE_BIN`, and runs
   `providence install --wizard --non-interactive --only-template`. This proves the
   wheel-packaged compiler can execute the install compile path, but it
   cannot prove the *published* release exposes assets, because publication
   hasn't happened yet at this point in the pipeline.
3. **Post-publication release gate** (`release` job, "Verify GitHub Release
   exposes standalone compiler assets") — after
   `softprops/action-gh-release` runs, queries the GitHub Release API for
   `github.ref_name` and fails if any required asset is not visible. This is
   the only gate that proves standalone clients can actually discover the
   assets.

The release-creation step sets `overwrite_files: true` so re-running the
workflow for an existing tag (e.g. to repair a release published without
assets) replaces the files instead of failing or leaving stale duplicates.

## Client resolution order

`CompilerRunner._locate_binary` (in
`packages/core/providence_core/src/providence_core/utils/compiler_runner.py`) resolves the
binary in this order:

1. `SDD_COMPILE_BIN` environment variable.
2. `<repo_root>/tools/sdd-compile/bin/providence-compile` (built via
   `make build-compiler`).
3. `sdd-compile` on `PATH`.
4. Native compiler asset packaged inside the installed `providence-core` wheel.
5. Cached/downloaded release asset matching the installed `providence-cli` version
   (tries both `vX.Y.Z` and `VX.Y.Z` tags), skipped when
   `SDD_COMPILE_NO_DOWNLOAD` is set.

A downloaded binary is only trusted if its SHA256 matches the entry in the
release's `SHA256SUMS`; a missing manifest or missing checksum entry raises
`CompilerRunnerError` rather than running an unverified binary.

Set `SDD_COMPILE_DEBUG_DOWNLOADS=1` to log every URL attempted (and its
HTTP outcome) to stderr — useful when diagnosing which tag/asset combination
a standalone client is trying.

## Emergency recovery

See the
[Standalone Compiler Release Assets Missing](../../incidents/PLAYBOOKS.md#standalone-compiler-release-assets-missing)
playbook. In short: manual `gh release upload` is an emergency-only
recovery path, never the steady-state process — always follow it with a new
tag that goes through the full, now-fixed CI pipeline.
