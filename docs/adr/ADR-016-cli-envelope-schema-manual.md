# ADR-016 - CLI Envelope Schema Is Manually Maintained

**Status:** Accepted
**Date:** 2026-07-24
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

ADR-006 made `CommandResult` and `CommandError` the canonical JSON envelope for
`providence_cli` output. The implementation uses frozen dataclasses in
`packages/interfaces/providence_cli/src/providence_cli/shared/contracts.py`.

The residual A1 work asked whether the envelope should move to Pydantic with a
generated schema or stay as dataclasses with a manually maintained schema.

## Decision

Keep the runtime envelope as frozen dataclasses and publish a manually
maintained JSON Schema at:

`tests/contract/schemas/cli_command_envelope.schema.json`

Contract tests validate the existing builders against that schema. This keeps
the runtime shape stable while giving consumers a concrete schema artifact.

## Rationale

- The current dataclasses are small, stable, and already used by CLI services.
- Migrating to Pydantic would add compatibility risk without changing the
  envelope semantics.
- A manual schema is acceptable because tests validate representative success
  and error envelopes against it.

## Consequences

- Any change to `CommandResult` or `CommandError` must update the schema and the
  contract tests in the same change.
- Breaking envelope changes require a `schema_version` bump and an ADR or
  changelog entry.
- `make generate-schemas` does not own this schema unless the project later
  migrates the envelope model to Pydantic.

## Links

- Superset decision: [ADR-006](ADR-006-cli-canonical-json-envelope.md)
- Runtime model: `packages/interfaces/providence_cli/src/providence_cli/shared/contracts.py`
- Schema: `tests/contract/schemas/cli_command_envelope.schema.json`
