# Windows Standalone Troubleshooting — `providence init --default`

This guide covers diagnosing failures of the compiler pipeline on standalone Windows
clients, where `sdd` is installed via pip/uv and the Go `sdd-compile` binary is resolved
from the packaged wheel or downloaded from GitHub Releases.

Reference: mission `20260718T235134Z` analysis (`.analysis/refined/20260718T235134Z/`).

## Architecture Recap

`providence init --default` runs governance generation, which invokes the Go `sdd-compile`
binary through `CompilerRunner`. The binary is resolved in this order:

1. `SDD_COMPILE_BIN` environment variable
2. Repo-local build at `tools/sdd-compile/bin/` (development checkouts only)
3. `sdd-compile` on `PATH`
4. Binary packaged inside the `providence-core` wheel (`providence_core/_native/`)
5. Download from GitHub Releases matching the installed `providence-cli` version
   (SHA256-verified, cached under `%USERPROFILE%\.providence\bin`)

## First Diagnostic Step: `providence doctor compiler`

Before any manual digging, run:

```powershell
providence doctor compiler
```

It prints a read-only JSON report covering everything the manual runbook below
inspects by hand: which binary was resolved and by which rule, its version, the
CLI↔binary version handshake state, the `%USERPROFILE%\.providence\bin` cache contents,
whether the installed wheel bundles `_native` binaries, and a dry validation of
`.providence\compiled`. A `handshake.status` of anything other than `ok` /
`skipped_dev_binary`, or stale entries in `cache.entries`, usually identifies the
problem immediately. Attach this JSON to any escalation.

A standalone Windows client normally hits step 4 or 5. Known failure classes, in order
of historical impact:

1. **Git symlink stubs in packaged specs — root cause found and fixed (2026-07-19).**
   `providence_core` shipped `mandate.spec`/`guidelines.dsl` as git symlinks; Windows clones
   with `core.symlinks=false` (the default) checked them out as 24-byte text stubs.
   The wizard scaffold copied the stub into `docs-meta`, the governance pipeline parsed
   **zero mandates**, and validation failed with
   `core_fingerprint_valid: invalid core fingerprint: empty`. This affected
   **source installs only** (`uv tool install git+...`); release wheels dereference
   symlinks and were never affected. Fixed at the root: the specs are now real files, a
   CI guard bans tracked symlinks repo-wide, and `PipelineBuilder` fails fast with an
   actionable error (`Parsed 0 mandates from <path>...`) instead of emitting empty
   artifacts. If you see that fail-fast error on an older install, upgrade to a release
   containing the fix or install from the release wheelhouse.
2. **Version skew** (secondary, still open — pending hardening T3/T5): a cached or
   mismatched `sdd-compile.exe` whose artifact schema differs from what the installed
   CLI expects. Diagnosed manually with the runbook below.

## Symptom: `core_fingerprint_valid: invalid core fingerprint: empty`

First check failure class 1 above: on releases with the fix, PHASE 2 logs the failing
validation checks and the pipeline fails fast on zero parsed mandates, naming the
offending source file. For version-skew suspects (class 2), work through the steps
below in order.

### 1. Inspect the generated metadata

```powershell
Get-Content generated\client\compiled\metadata-core.json
```

If `fingerprint` is absent or empty, the compile step was performed by a binary whose
metadata schema does not match the validator — almost always an outdated binary.

### 2. Identify the binary actually used and its version

```powershell
$bin = Get-ChildItem -Recurse "$env:USERPROFILE\.providence\bin" -Filter "sdd-compile*.exe" |
       Select-Object -First 1 -ExpandProperty FullName
& $bin version
```

> **PowerShell note:** you must prefix the call with `&` (the call operator).
> `$bin validate --dir ...` without `&` is a PowerShell parser error
> (`Token 'validate' inesperado`), not an sdd failure.

Compare the reported version with the installed CLI version (`pip show providence-cli` or
`uv tool list`). Any mismatch is suspect.

### 3. Clear the cached binary

The download cache is keyed by version but stale entries survive upgrades:

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.providence\bin"
providence governance generate --verbose
```

This forces re-resolution (packaged wheel binary first, fresh download otherwise).

### 4. Pin a known-good binary explicitly

If a current binary is available (from a fresh release asset or a local build):

```powershell
$env:SDD_COMPILE_BIN = "C:\path\to\sdd-compile-windows-amd64.exe"
providence governance generate --verbose
```

`SDD_COMPILE_BIN` takes precedence over every other resolution rule.

### 5. Check whether the installed wheel bundles the binary

```powershell
python -c "import providence_core, pathlib; p = pathlib.Path(providence_core.__file__).parent / '_native'; print(list(p.glob('*')) if p.exists() else 'NO _native directory')"
```

If the wheel does not bundle `sdd-compile-windows-amd64.exe`, the standalone client
depends entirely on the release download path. In that case verify (step 2) that the
downloaded tag matches the installed CLI version — dev-scheme package versions fall back
to the nearest base release tag, which can produce exactly this schema skew.

## Symptom: `invalid_governance_path: ...\.providence\compiled`

`providence governance generate` refuses a `.providence\compiled` directory left in an inconsistent
state by a previously failed run. Re-run after resolving the compiler failure above; if
the error persists, remove the stale `.providence\compiled` directory and regenerate.

## Debugging Downloads

Set `SDD_COMPILE_DEBUG_DOWNLOADS=1` to log every release URL attempted, HTTP status, and
payload size to stderr. TLS verification uses the system trust store plus `certifi`;
corporate TLS-intercepting proxies additionally require `SSL_CERT_FILE`.

## Escalation

If the steps above do not identify the cause, capture and attach:

- `metadata-core.json` content (step 1)
- `& $bin version` output vs installed CLI version (step 2)
- `providence governance generate --verbose` output with `SDD_COMPILE_DEBUG_DOWNLOADS=1`
