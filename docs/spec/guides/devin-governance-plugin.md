# Providence Governance Projection for Devin

Generates a self-contained, distributable Devin plugin bundle from this repository's
`.providence/skills/` registry, in **Soft/Standalone** profile.

## What Soft/Standalone means

- Works without Providence, without network, without any runtime Python/Go/Node dependency.
- Reports `policy_source=embedded_snapshot` and `assurance=reduced` — both in `AGENTS.md`
  (always loaded) and via a `SessionStart` hook that injects the same disclosure into the
  agent's context at session start.
- Is never represented as equivalent to a connected, Hard/Connected Providence session.

Hard/Connected mode (a live Providence probe/handshake) is **not implemented**. It requires
a separate RFC — see `docs/spec/guides/RFC_PROCESS.md` — because it would introduce a new Providence
external integration protocol.

## Build

```bash
providence devin build
# optional: providence devin build --dest ./some/other/path
# governance-only bundle, no Providence skill catalog: providence devin build --no-skills
```

Or from Python:

```python
from providence_adapters.devin import DevinPluginGenerator

DevinPluginGenerator().generate(output_dir=repo_root)
# or: DevinPluginGenerator().generate(output_dir=repo_root, include_skills=False)
```

`include_skills` defaults to `True`. Each embedded skill's "Allowed CLI" commands
assume the `providence` CLI is installed in the Devin environment — a dependency the base
governance summary (`AGENTS.md` + `rules/`) does not have. Pass
`include_skills=False` (or `--no-skills`) for a bundle that is governance context
only, with no `skills/` directory and no `"skills"` key in `plugin.json`.

Output: `dist/devin-plugin/` (gitignored — treat like any other build artifact).

## Install into Devin

```bash
devin plugins install ./dist/devin-plugin
```

## Bundle contents

| Path | Role |
|---|---|
| `.devin-plugin/plugin.json` | Plugin manifest (name, version, license, skill paths) |
| `AGENTS.md` | Always-on assurance/precedence disclosure + governance summary Tier A (index) |
| `rules/providence-summary.md` | Governance summary Tier B (condensed detail), loaded contextually |
| `rules/sdd-soft-governance-behavior.md` | Curated, CLI-independent behavioral rules (git safety, escalation, mandate precedence) |
| `skills/{name}/SKILL.md` | One per canonical Providence skill in `.providence/skills/registry.json` — omitted entirely when built with `--no-skills` |
| `hooks.json` + `hooks/session-start-assurance.sh` | Injects the Soft/Standalone disclosure into every session |
| `metadata/provenance.json` | Plugin version, compiler version, source revision, embedded policy digest, embedded governance summary digest, soft governance ruleset version, profile |
| `LICENSE` | Copied from the source project's root `LICENSE`, if present |

## Providence governance summary (mandates & guidelines)

The plugin embeds a summary of Providence itself — not just skills — so a session
using only the Soft/Standalone bundle (no governance skill, no live connection) still
has a picture of the mandates and guidelines it operates under. This is a two-tier
summary, kept deliberately separate from the skills digest:

- **Tier A — index, always-on (`AGENTS.md`, "Providence Summary" section):**
  governance fingerprint, workspace version, mandate count, and a plain list of
  mandate **IDs + titles only** — no descriptions, plus guideline **category names
  only** (one per `.providence/source/guidelines/*.md` file). This is an index, not policy
  prose, so it stays small enough for content that's loaded every session.
- **Tier B — condensed detail, contextual (`rules/providence-summary.md`):** one
  section per mandate and guideline category, with a condensed description **only
  when the canonical source has real content for it**. When a mandate's or
  guideline's canonical source is the placeholder `"No description available"`,
  Tier B renders the section as `"(no summary available in source)"` — it never
  fabricates a summary from an incomplete source. As of this writing, this repo's
  own `.providence/source/mandates/mandates.md` has placeholder text for all 16 mandates,
  so a bundle built from this repo will show `"(no summary available in source)"`
  throughout Tier B; that reflects the source, not a bug in the generator.

A full mandate/guideline text copy (a "Tier C") was considered and rejected — it
would raise the same policy-divergence risk the skills projection already accepts,
without a compensating benefit over the condensed Tier B.

`AGENTS.md` also prints a coverage line — `Mandates with a source description: X/Y`
— computed from the same parsed data, so the emptiness of Tier B (when the source
has no descriptions) is visible at the always-on level, without opening
`rules/providence-summary.md` to discover it.

**Staleness disclosure:** the governance summary has its own
`embedded_governance_summary_digest` in `provenance.json`, printed in both `AGENTS.md`
and `rules/providence-summary.md`. It is computed independently of
`embedded_policy_digest` (which stays skills-only) — changing skill content never
changes the summary digest, and changing mandate/guideline content never changes the
skills digest. Compare digests across two builds to tell which half of the embedded
content changed.

## Soft governance behavior ruleset

`rules/sdd-soft-governance-behavior.md` is a small, **hand-curated** (not
auto-parsed) set of behavioral rules distilled from this repository's
`.providence/agent-instructions.md`: git safety (never execute state-modifying git
commands autonomously), escalate-on-incomplete-context, and mandates-outrank-
guidelines precedence. It deliberately excludes anything that assumes a live `providence`
CLI connection — the M015 handshake procedure, `execution_gate` /
`intake_index_mode` semantics, fingerprint-diffing instructions — since those only
apply in Hard/Connected mode, which this plugin does not implement; embedding them
in a Soft/Standalone bundle would point a disconnected session at signals it will
never receive.

Its `soft_governance_ruleset_version` in `provenance.json` is a plain version
string a maintainer bumps by hand when the curated content changes — unlike the two
content digests above, it does not recompute automatically on every build, because
the ruleset is not mechanically derived from `agent-instructions.md` (that source
has no stable per-rule structure to parse against safely).

## Precedence order

1. Provider or organization safety controls (Devin's own permissions/config).
2. Connected Providence hard policy (not active in Soft/Standalone).
3. Project canonical policy (the consuming project's own `.providence/`, if present).
4. Embedded Providence snapshot (this plugin's `skills/`).
5. Provider local rules (`.devin/config.json`, project `AGENTS.md`, `rules/`).
6. User task instructions.

## Canonical source

This plugin is a generated projection, never a policy source. Canonical Providence governance stays
in this repository's `.providence/`. See `metadata/provenance.json` in a built bundle for the exact
source revision it was generated from.

## Known limitations

- `SKILL.md`'s `triggers` frontmatter sub-schema is rendered as a flat list — Devin's exact
  user/model trigger split was not fully documented publicly as of 2026-08-17. Re-verify
  against `docs.devin.ai/cli/extensibility/skills/creating-skills` before the next schema bump.
  See `docs/spec/guides/devin-plugin-provider-surface-evidence.md`.
- Hard/Connected mode is out of scope (see above).
- This repo's own `.providence/source/mandates/mandates.md` has placeholder
  `"No description available"` text for all current mandates, so Tier B of the
  governance summary is index-only in practice for a bundle built from this repo
  today. Fixing that source content is tracked separately, not by this feature.
- The plugin bundle has been verified structurally and against the real `.providence/skills/`
  registry, but has not yet been installed into a live Devin CLI session. Run
  `devin plugins install ./dist/devin-plugin` against an actual Devin CLI installation
  before treating this as production-ready.
