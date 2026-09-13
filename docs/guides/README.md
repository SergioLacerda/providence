# Providence README — Detailed Workflows

This document contains the operational details that are intentionally kept out of
the repository landing README.

## Client Onboarding Details

The basic onboarding flow is:

```bash
uv tool install providence-cli --find-links "https://github.com/SergioLacerda/providence/releases/expanded_assets/v1.0.15"
cd your-project
providence install --wizard
providence init --default
providence governance validate
```

Do not use `uv tool install git+https://...#subdirectory=packages/interfaces/providence_cli`
— it cannot resolve `providence-cli`'s `providence-*` sibling packages
(this is a multi-package monorepo; none of them are published to PyPI on
their own) from outside a full local workspace checkout, tag-pinned or not.

For the complete client installation guide, platform notes, release artifacts,
and troubleshooting, see [Client Onboarding](CLIENT_ONBOARDING.md).

## Core Workflows

### Governance

```bash
providence governance compile
providence governance validate
providence governance score --verbose
providence governance keygen --key-id my-org-01
providence governance sign --key-id my-org-01
```

`providence governance sign --key-id <id>` reads
`.providence/trust/<id>.key` unless `--key-path` is provided.

### Runtime and Audit

```bash
providence runtime status
providence audit
providence skills list
providence skills describe sdd-validate-governance
```

### Agent Onboarding After Governance Activation

```bash
providence skills list
providence skills describe sdd-validate-governance
providence skills run sdd-validate-governance
```

### Quality Gates

```bash
providence test run
providence lint run
make pre-delivery
```

Complete command reference: [CLI Reference](../spec/reference/commands/cli.md).

## Release Verification

Tagged releases publish checksums and standalone `sdd-compile` binaries. Verify a
downloaded binary with:

```bash
sha256sum -c SHA256SUMS --ignore-missing
python -m sigstore verify github \
  --cert-identity "https://github.com/SergioLacerda/providence/.github/workflows/release.yml@refs/tags/<tag>" \
  dist/sdd-compile-linux-amd64
```

Releases also carry an [SLSA build provenance
attestation](https://slsa.dev/) over the `dist/` directory.

## Security and Trust

Providence uses a fail-closed governance model for sensitive execution paths.
Governance artifacts can be signed with Ed25519 keys, runtime validation can
reject missing or invalid signatures, and compliance events are emitted for
auditability.

```bash
export SDD_SIGNATURE_MODE=strict
```

Further reading: [Security](../spec/reference/SECURITY.md) and the
[mandatory human review policy](../spec/canonical/core/policies/P003_MANDATORY_HUMAN_REVIEW.md).

## Local Docker Build

`make docker-build` requires Docker BuildKit and the `docker buildx` plugin.
Install the plugin before running the target if Docker reports that BuildKit or
the `buildx` component is missing.
