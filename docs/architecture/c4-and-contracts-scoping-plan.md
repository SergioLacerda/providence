# C4 Diagrams & Per-Component Contracts — Scoping Plan

This is the scoping decision for backlog item A1 (from
`.analysis/pending/20260708-critique-complex-items-analysis/`): which additional C4
diagrams are actually needed, what format per-component API contracts should take, and
how to add both without duplicating structure that already exists. It is a plan, not
the diagrams/contracts themselves — see [Future Work](#future-work) for the resulting
backlog.

## What Already Exists

`docs/architecture/` already contains C4 Level 1 (Context) and Level 2 (Containers)
diagrams, plus one Level 3 (Components) diagram for `providence_runtime`
([`c4-components-runtime.md`](c4-components-runtime.md)). All three are Mermaid, wired
into `mkdocs.yml` nav, and linked from other docs (e.g.
`docs/guides/LEARNING_INTEGRATION.md`). `c4-context.md` dates to the initial repo
setup; `c4-components-runtime.md` was last touched shortly before this scoping mission
started — both predate the backlog card that motivated this plan, so any estimate that
assumed diagrams "from scratch" was stale before this scoping even began.

No OpenAPI spec exists anywhere in the repo, and no genuinely inbound HTTP-shaped
surface was found that would justify adding one in this pass.

## Diagrams (L3 — Components)

| Package | Decision | Rationale |
|---|---|---|
| `providence_cli` | **Recommended** | Largest package (~21k source LOC), the primary contributor entrypoint, and the most likely place for a new contributor to get lost. Draft one L3 diagram covering CLI command dispatch → handler → shared envelope flow, mirroring the style of [`c4-components-runtime.md`](c4-components-runtime.md). |
| `providence_core` | **Optional, deferred** | Smaller, more stable, narrower authority boundary by design — lower documentation-churn risk if it waits for a future pass. Not committed in this plan's scope. |
| Context (L1) / Containers (L2) | **No changes** | Both are current and accurate as-is. |

## Contracts (Per-Component)

**Primary mechanism: extend the existing Pydantic → JSON Schema pipeline**
(`tests/contract/models.py` + `make generate-schemas`) — not a new, parallel format.
This was a user decision made during scoping discovery, aligned with how governance
artifacts already work.

1. **Inventory gap**: `packages/interfaces/providence_cli/src/providence_cli/shared/contracts.py`
   defines the canonical CLI JSON envelope (`CommandResult`, `CommandError`) as frozen
   dataclasses — not Pydantic. This is the one cross-boundary payload found with no
   Pydantic model backing it. Open decision (see Future Work): keep as dataclasses
   with a hand-maintained JSON Schema, or migrate to Pydantic for schema
   auto-generation consistency with the governance-artifact pattern.
2. **Already covered**: payloads that already have Pydantic models (governance
   artifacts, via `tests/contract/models.py`) need no new work — `make
   generate-schemas` already regenerates their schemas from the models.
3. **OTLP exporter**: `_otlp_http_exporter.py` is an *outbound* client sending spans in
   the externally-specified OTLP/JSON wire format — not an OpenAPI candidate. If
   internal consistency-checking is ever wanted, the payload shape built by
   `_build_otlp_payload` could get a JSON Schema like everything else, but this is low
   priority and not part of this plan's committed scope.

**No OpenAPI** in this pass, for the reason above (no inbound HTTP-shaped surface to
document). Revisit if the repo ever grows a served HTTP API.

## Where Things Live / Sync Mechanism

- **New L3 diagrams** go to `docs/architecture/c4-components-<pkg>.md`, following the
  exact existing file/README/`mkdocs.yml`-nav pattern — see this directory's
  [README](README.md).
- **Contract schemas** extend `tests/contract/schemas/` alongside
  `governance_core.schema.json`, regenerated via the existing `make generate-schemas`
  target. No new tooling — new models/targets register with the existing pipeline.
- **Sync/drift prevention**: schemas are generated *from* Pydantic models, not
  hand-written in parallel — any new contract should follow that same discipline
  rather than adding a doc that can drift from the code it describes.

## Future Work

The items below are the resulting backlog — none of them are executed by this plan
itself:

1. Draft `docs/architecture/c4-components-cli.md` (L3 diagram for `providence_cli`) and wire
   it into `mkdocs.yml` nav.
2. Decide and implement: keep `CommandResult`/`CommandError` as frozen dataclasses with
   a hand-maintained JSON Schema, or migrate to Pydantic.
3. Extend `tests/contract/schemas/` + `make generate-schemas` for any new component
   contracts identified by item 2 (and any others surfaced while drafting item 1).
4. Optional/deferred: `docs/architecture/c4-components-core.md` (L3 diagram for
   `providence_core`).
