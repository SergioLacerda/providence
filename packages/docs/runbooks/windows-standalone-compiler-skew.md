# Windows Standalone Compiler Skew

Verification state: documented

## Symptoms

- `providence init --default` fails on Windows during governance generation.
- Validation reports `core_fingerprint_valid: invalid core fingerprint: empty`.
- Generated metadata lacks a valid `fingerprint`.
- The CLI and `sdd-compile.exe` appear to use different artifact schemas.

## Diagnosis

1. Run the read-only compiler diagnostic first:

   ```powershell
   providence doctor compiler
   ```

2. Inspect generated metadata:

   ```powershell
   Get-Content generated\client\compiled\metadata-core.json
   ```

3. Identify the compiler binary and version:

   ```powershell
   $bin = Get-ChildItem -Recurse "$env:USERPROFILE\.providence\bin" -Filter "sdd-compile*.exe" |
          Select-Object -First 1 -ExpandProperty FullName
   & $bin version
   ```

4. Compare the compiler version with the installed Providence CLI version.

## Resolution Steps

1. Clear the cached compiler binary:

   ```powershell
   Remove-Item -Recurse -Force "$env:USERPROFILE\.providence\bin"
   providence governance generate --verbose
   ```

2. Prefer a release wheelhouse install when possible.
3. If needed, pin a known-good compiler explicitly:

   ```powershell
   $env:SDD_COMPILE_BIN = "C:\path\to\sdd-compile-windows-amd64.exe"
   providence governance generate --verbose
   ```

4. Re-run:

   ```powershell
   providence governance validate
   providence runtime status
   ```

## Rollback

1. Remove `SDD_COMPILE_BIN` if it points to a temporary binary.
2. Reinstall the Providence CLI from the last known-good release wheelhouse.
3. Regenerate governance from authored sources.

## Post-Incident

- Attach `providence doctor compiler` output to the support issue.
- Update release notes if a new version-skew class is confirmed.

## Evidence To Attach

- `providence doctor compiler` JSON
- `metadata-core.json`
- compiler version
- installed CLI version
- `providence governance generate --verbose` output

## Sources

- `docs/guides/windows-standalone-troubleshooting.md`
- `docs/guides/CLIENT_ONBOARDING.md`
- `docs/guides/release/STANDALONE_COMPILER_ASSETS.md`
