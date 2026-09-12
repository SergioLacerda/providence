# Providence Documentation

This page is the routing surface for the published docs site. It points readers
to the shortest path by intent and leaves canonical technical detail in the
deeper docs tree.

## Start Here

| You want to... | Start here |
|---|---|
| bootstrap governance in a project | [`guides/CLIENT_ONBOARDING.md`](./guides/CLIENT_ONBOARDING.md) |
| contribute to this repository | [`guides/ONBOARDING.md`](./guides/ONBOARDING.md) |
| understand the architecture | [`architecture/README.md`](./architecture/README.md) |
| understand governance source vs runtime output | [`governance-runtime-model.md`](./governance-runtime-model.md) |
| inspect CLI commands and contracts | [`spec/reference/commands/cli.md`](./spec/reference/commands/cli.md) |
| understand runtime agent entrypoints | [`runtime/protocols/AGENT_ENTRYPOINT.md`](./runtime/protocols/AGENT_ENTRYPOINT.md) |
| recover from known operational failures | [`runbooks/README.md`](./runbooks/README.md) |
| navigate the broader docs corpus | [`guides/TECHNICAL_GUIDE.md`](./guides/TECHNICAL_GUIDE.md) |

## Documentation Map

### Getting Started

- `guides/CLIENT_ONBOARDING.md`
- `guides/ONBOARDING.md`
- `guides/FAQ.md`

### Guides

- `guides/RUNTIME_API_INTEGRATION.md`
- `guides/FRONTEND_SELECTOR.md`
- `guides/SDD_FOLDER_REFERENCE.md`

### Runbooks

- `runbooks/README.md` — reusable operational procedures
- `incidents/PLAYBOOKS.md` — incident-response playbooks
- `maintenance/landing-site-runbook.md` — site publication and selector maintenance

### Reference

- `spec/reference/commands/cli.md`
- `spec/reference/SECURITY.md`
- `spec/reference/templates/AI_CONTEXT_AWARE_TEMPLATE.md`
- `spec/reference/templates/CONTEXT_MANAGEMENT_STANDARDS.md`

### Architecture and Governance

- `architecture/README.md`
- `governance-runtime-model.md`
- `runtime/protocols/AGENT_ENTRYPOINT.md`
- `runtime/protocols/AGENT_RUNTIME_PROTOCOL.md`
- `adr/INDEX.md`

## Reading Strategy

For human readers:

- start with onboarding or architecture, depending on your task
- use reference pages only when you need exact contracts or commands

For agents:

- prefer path-based context loading
- start from `runtime/protocols/AGENT_ENTRYPOINT.md`
- use `guides/TECHNICAL_GUIDE.md` as the broader navigation index

## Notes

- This docs surface is intentionally route-oriented; canonical technical content
  remains in `docs/spec/`, `docs/runtime/`, `docs/architecture/`, and `docs/adr/`
- `docs/runbooks/` is the reusable operational procedure surface; `docs/guides/`
  remains a mixed guide/reference area
- Multi-version docs and generated API reference are deferred follow-up tracks,
  not part of this intro-surface cleanup
