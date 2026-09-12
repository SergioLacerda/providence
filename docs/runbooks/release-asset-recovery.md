# Release Asset Recovery

Verification state: documented

## Symptoms

- Standalone clients cannot resolve `sdd-compile`.
- Release wheel or source install expects a native compiler asset that is missing.
- Windows or Linux smoke install fails after a release.
- Users fall back to manual compiler downloads.

## Diagnosis

1. Check the release workflow result.
2. Confirm whether the wheel bundles native compiler binaries.
3. Inspect the release assets for the expected platform binary.
4. For client failures, collect `providence doctor compiler` output.

## Resolution Steps

1. If this is an active release incident, follow the relevant incident playbook.
2. Upload missing release assets only as an emergency recovery path.
3. Prefer issuing a corrected release over relying on manual uploads.
4. Re-run install smoke checks on supported platforms.

## Rollback

1. Mark the affected release as degraded or superseded.
2. Direct users to the last known-good release wheelhouse.
3. Remove temporary manual instructions after the corrected release exists.

## Post-Incident

- Record the incident in `docs/incidents/FAILURE_LEDGER.md`.
- Update `docs/incidents/PLAYBOOKS.md` if the recovery sequence changed.
- Add or strengthen release smoke coverage.

## Evidence To Attach

- release workflow URL
- asset list
- wheel contents
- client `providence doctor compiler` output
- smoke install logs

## Sources

- `docs/guides/release/STANDALONE_COMPILER_ASSETS.md`
- `docs/guides/release/RELEASE_READINESS_V1.md`
- `docs/incidents/PLAYBOOKS.md`
