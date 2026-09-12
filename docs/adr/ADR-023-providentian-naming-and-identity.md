# ADR-023 — Providentian Naming and Identity Contract

**Status:** Proposed
**Date:** 2026-09-07
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

Two architecture analyses (`.analysis/pending/ACHADOS_E_MELHORIAS_PROVIDENTIA.md`,
`.analysis/pending/nova_arquitetura.txt.txt`) diagnose that `ask` accumulated kernel
responsibilities (intake, intent classification, gate, context, budget, dossier, handoff)
and propose consolidating the product identity under a new name, with SDD demoted to a
policy pack under a provider-agnostic governance kernel. `nova_arquitetura.txt.txt` §14
("Fase 0 — contrato de nomenclatura") explicitly calls for a naming ADR as a prerequisite
before any public rename — this document is that Fase 0.

A first identity decision was already made during mission
`20260907-landing-page-providentia-migration` (see
`.analysis/refined/20260907-landing-page-providentia-migration/design.md`, decision D-1):
the landing page adopts the Providentian identity as its target, ahead of the sequencing
the source documents themselves recommend (which places public-surface renames last). This
ADR formalizes that vocabulary for the rest of the project, without by itself approving or
starting the backend reorganization (tracked separately, out of scope here).

## Decision

Adopt the following canonical vocabulary:

| Concept | Name | Status |
|---|---|---|
| Product | **Providentian Agent Governance** | current standard |
| Short name | **Providentian** | current standard |
| Philosophy | **Providentia** | current standard |
| CLI | `provident` | **current standard** for every new entry surface — not a future target |
| Primary entry | `provident "<intent>"` | **current standard** |
| Slash command | `/provident` | **current standard** — new skill/slash-command integrations are modeled on this pattern, not on `sdd-*` |
| SDD specification | policy/plugin under the Providentian kernel | current standard |

**Legacy terms** — active deprecation, not an indefinitely co-equal default:

- `sdd`, `providence ask`, `/sdd-ask` stop being the reference pattern for any new work — no new
  skill, command, or integration is modeled on them starting with this ADR.
- They continue to exist **only as a compatibility adapter** for existing dependents, with
  structured deprecation warnings and usage telemetry (per
  `ACHADOS_E_MELHORIAS_PROVIDENTIA.md` §5.2), until removal in a major version (§8, P3).
- Any prompt, skill template, or CLI wrapper written **from this point on** — in this or in
  future missions — follows the `provident`/`/provident` pattern, even before the backend
  reorganization (SQ-2, out of scope here) is complete. This ADR does not block adopting the
  new pattern at the surface level (names, prompts, commands); it does not, by itself, force
  an immediate rewrite of everything that already exists on the old pattern.

**What stays called SDD:** the Spec Driven Development specification, its mandates,
templates, and the corresponding policy pack.

**What stops being called Ask:** kernel responsibilities — intake, intent classification,
gate, routing, context/budget. These migrate conceptually to a Governed Intake / Context
Broker, no longer tied to the `ask` name.

**Surfaces already authorized to adopt the name now:** the landing page (`apps/landing`),
via the already-refined migration mission
(`docs/migration/2026-09-07-landing-page-providentia-migration.md`); any new prompt,
skill definition, or CLI-facing surface going forward, per the paragraph above.

**Surfaces not authorized by this ADR:** repository rename, Python/Go package renames, the
default executable, the root README — these remain Providence until a separate, explicit
decision.

## Consequences

**Positive:**

- Gives future contributors a stable vocabulary for the in-progress identity, instead of
  depending on two non-normative analysis documents.
- Unblocks the landing-page migration mission with a formal reference, rather than an
  isolated, informal per-mission decision.
- New prompts, skills, and CLI-facing surfaces have one unambiguous pattern to follow
  starting now, instead of two competing patterns during the transition.

**Negative:**

- Creates a window where the landing page and any new prompts/skills use a name the rest of
  the product (CLI binary, packages, repository) does not yet use — visible inconsistency
  risk, consciously accepted.
- Naming the new pattern "current standard" ahead of the backend kernel existing means
  `provident`/`/provident` can appear in prompts and screens (landing page, skills) without
  a runtime implementation of their own yet — anyone who literally tries `provident` falls
  back to `providence ask` until SQ-2 lands. This must be signaled as "preview" wherever no real
  `provident` binary exists yet (e.g. `instalacao.astro`), not treated as a bug.
- Does not resolve a removal deadline for the legacy aliases; that is set when SQ-2 (backend
  reorganization) actually starts.

## Alternatives Considered

- **Name nothing yet, wait for the backend reorganization to finish first.** Rejected — the
  landing page already needs this vocabulary now (migration already refined and accepted),
  and new work should not keep being modeled on a name already diagnosed as a kernel-shaped
  accident.
- **Rename everything at once (`ask_*` → `provident_*`).** Rejected — both source documents
  call this a "false simplification"; it preserves the coupling and grows the diff without
  improving the architecture.
- **Keep legacy and new patterns co-equal indefinitely, let call sites choose freely.**
  Rejected per explicit user direction: new work must default to the `provident`/`/provident`
  pattern, with legacy kept only for existing dependents under active deprecation.

## Links

- `.analysis/pending/ACHADOS_E_MELHORIAS_PROVIDENTIA.md`
- `.analysis/pending/nova_arquitetura.txt.txt`
- `.analysis/refined/20260907-landing-page-providentia-migration/design.md` (decision D-1)
- `docs/migration/2026-09-07-landing-page-providentia-migration.md`
