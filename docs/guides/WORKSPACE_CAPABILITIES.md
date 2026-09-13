# Workspace Capabilities

`master` and `client` remain artifact compatibility identifiers, not user roles.
Existing `.providence/profile` files continue to work unchanged. An optional
section separates operation eligibility, artifact selection, and audit policy:

```ini
[sdd]
type = client
name = example

[workspace]
capabilities = consume,author,publish
artifact_target = client
audit_mode = active
```

`consume` permits the wizard. `publish` permits the release command and requires
`author`. `author` declares authoring intent; it does not add a new restriction
to existing compile commands. These capabilities are local configuration, not
credentials or authorization to publish to an external service. Existing
governance gates remain in effect.

Without explicit capabilities, master derives consume/author/publish and client
derives consume. The existing master wizard warning remains. Unknown capabilities,
empty capability sets, and unsupported settings are rejected.

Artifact selection precedence is `--profile`, then `SDD_PROFILE`, then
`workspace.artifact_target`, then `sdd.type`. Only master/client targets are
accepted. Signed manifests, output directory names, and profile mismatch checks
retain their existing contracts. Explicit target overrides do not erase explicit
capabilities or audit configuration.

Audit precedence is a valid `SDD_LOGGING_MODE`, then `workspace.audit_mode`, then
the legacy profile default (master active, client passive). Passive still persists
mandatory events. Allowed explicit audit modes are passive, active, and strict.
The workspace setting is consumed by the compliance log writer; callers of the
standalone policy API without a workspace root retain the legacy defaults.

No profile migration or signed-artifact rewrite is required. Regenerating a legacy
profile preserves the optional workspace section. New operation eligibility is
limited to the already profile-aware release and wizard callbacks; it is not a
global command allowlist.
