# ADR-017 - Governance Signing KMS Is Deferred

**Status:** Accepted
**Date:** 2026-07-24
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

Governance artifacts can be signed with Ed25519 keys. Current signing uses the
native `sdd-compile` backend through `CompilerRunner.sign()`, with private keys
read from a local key path and trusted public keys stored in
`.providence/trust/trusted-keys.json`.

The residual A7 work asked for a KMS and rotation decision before any provider
integration code.

## Decision

Do not implement a KMS provider in this stage.

Keep local Ed25519 signing and trusted keyring validation as the supported
model. Treat KMS integration as a separate future demand that must name the
provider and operating model before code is written.

## Current Lifecycle

1. `providence governance keygen --key-id <id>` creates a private key and matching
   public key material.
2. `providence governance sign --key-id <id>` signs compiled governance artifacts with
   the native Ed25519 backend.
3. Signing writes `.sig` manifests beside compiled artifacts.
4. The trusted keyring lives at `.providence/trust/trusted-keys.json`.
5. Runtime validation resolves the keyring and validates compiled artifact
   signatures according to the configured signature mode.

## KMS Scope Decision

KMS custody is not selected. AWS KMS, GCP KMS, Azure Key Vault, and self-hosted
HSM/KMS options remain unchosen.

If KMS is pursued later, the next demand must decide whether KMS owns:

- only the signing private key;
- the verification keyring distribution path;
- both signing custody and verification key distribution.

## Rotation Plan For Current Model

- Introduce a new key id while keeping the previous public key in the trusted
  keyring.
- Sign new artifacts with the new key id during the overlap window.
- Keep old public keys trusted until supported signed artifacts age out.
- Mark retired keys in the keyring before removal.
- Roll back by signing again with the previous active key while both public keys
  remain trusted.

## Required Preflights Before Future KMS Code

- Provider and region/account ownership are documented.
- Local development fallback is defined.
- CI access model and failure behavior are defined.
- Signature validation behavior is unchanged for consumers.
- Rotation and rollback are covered by tests or a documented manual procedure.

## Consequences

- A7 is closed for this residual as a decision artifact, not as KMS
  implementation.
- No runtime signing or verification code changes are authorized by this ADR.
- A future KMS implementation must be opened as a separate scoped demand.
