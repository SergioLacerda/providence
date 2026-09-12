# ADR-018: Profile Label vs. Route ID Decoupling

## Status

Accepted

## Context

The compact governance footer (`format_governance_footer`, in `providence_skills`)
already emits the `PROVIDENCE GOVERNANCE` prefix, but its `profile=` field either
carried a constant (`"default"`, hardcoded at the `providence skills run <id>` CLI
call site) or the workspace deployment type (`client`/`master`, read from
`.providence/profile`) — never the identity of the skill/command actually
invoked. A refinement proposal
(`.analysis/refined/20260912-providence-profile-brand-refinement/`) requested
that running a skill like `sdd-diagnose` show a Providence-branded profile label
(`providence-diagnose`) in the footer, on the assumption that the skill id was
already flowing into `profile=` somewhere.

That assumption did not hold: a full-repo grep and code trace found no call site
that ever passed a skill id as `profile`. Implementing the request therefore
required two decisions, not one: (1) how to turn a legacy `sdd-*` id into a
Providence-branded *display* string, and (2) whether `profile=` should start
carrying the invoked skill's identity at all, since today it means something
else (a workspace/enforcement profile).

Legacy `sdd-*` skill and command ids (`sdd-ask`, `sdd-diagnose`, `sdd-correct`,
`sdd-converge`, `sdd-organize`, `sdd-pipeline`, `sdd-validate-governance`,
`sdd-review-architecture`, `sdd-compress-context`, `sdd-harness`, and others)
remain the real registry identifiers — renaming them was explicitly out of scope
(compatibility risk: skill lookup, handshake declarations, fallback routing,
existing `/sdd-*` slash commands, and external callers all depend on the current
ids).

## Decision

### 1. Profile labels are display-only

`format_governance_footer()` resolves its `profile` argument through a new pure
function, `resolve_profile_label()` (`providence_skills.profile_labels`): any
value starting with `sdd-` becomes `providence-<suffix>`; every other value
(`default`, `client`, `master`, an already-resolved `providence-*` label, an
empty string) passes through unchanged. The resolver is a **rule**, not a
lookup table, so it covers every current and future `sdd-*` id without needing
an update per skill.

Structured output (`SkillRunResult.profile`, the JSON `data["profile"]` field)
keeps the raw id the caller passed in. Only the rendered footer *text* shows the
Providence label. This keeps the JSON contract's shape and meaning unchanged —
callers that parse `profile` still see the value they can look up in the skill
registry — while the human-facing string is branded consistently.

### 2. `profile=` now reflects the invoked skill for `skills run`

The single CLI call site that runs a named skill
(`providence_cli.commands.skills.run`) previously hardcoded
`profile="default"`, regardless of which skill was requested. It now passes the
skill's own id (`profile=name`). Because `profile` threads unchanged through
`SkillExecutor.run_skill` → `run_skill_flow` → every result builder
(`build_execution_result`, `build_missing_skill_result`,
`build_policy_blocked_result`) and every pipeline stage in
`run_composed_skill`, this single change is sufficient: no other skill-run code
path needed to change to get a correct, resolved footer and JSON `profile`
value.

`emit_pipeline_required` (the CLI-level guard that blocks `sdd-correct` before
`run_skill` is even called) was updated the same way for consistency, since it
also knows the requested skill's name at the point it emits its own JSON error
payload.

### 3. Workspace-type and ask-context profiles are unaffected

`providence ask`'s `profile` (the workspace deployment type — `client` or
`master`, from `.providence/profile`) is a different axis entirely: it
describes the workspace, not the invoked skill. It was left untouched. Because
values like `client`/`master` never start with `sdd-`, the resolver is a no-op
for them — there is no special-casing needed to keep this axis separate from
the skill-identity axis; the same function is safe to apply everywhere
`format_governance_footer` is called.

### 4. Compatibility policy

Legacy `sdd-*` ids remain the canonical, permanent registry identifiers.
`providence-*` strings are display labels only and are never accepted as
registry lookup keys, never stored as a skill's canonical id, and never used
for routing. Any future proposal to rename registry ids themselves (not just
their display label) requires a separate RFC and a documented deprecation
window — this ADR does not authorize that.

## Consequences

- `providence skills run sdd-diagnose --json` now reports
  `data["profile"] == "sdd-diagnose"` (previously always `"default"`) and
  `data["governance_footer"]` contains `profile=providence-diagnose`
  (previously `profile=default`).
- `providence skills run <name>` for every other registered skill gets the same
  treatment automatically, with no per-skill code change, because the fix is at
  the one call site the id already flows through.
- `providence ask`, `providence skills list/describe/export`, and any other
  context that does not run a specific skill keep reporting their existing
  `profile` value (workspace type or `"default"`) unchanged.
- A parallel audit
  (`docs/spec/decisions/2026-09-12-sdd-branding-audit.md`) found and fixed
  several *unrelated* residual `SDD`/`sdd` branding issues surfaced while
  investigating this change, including two genuine functional bugs: a
  `.claude` bootstrap hook and several runbook/playbook command examples that
  invoked a `sdd` binary that no longer exists (only `providence` is
  installed). Those fixes are tracked in that audit document, not this ADR,
  since they are independent of the profile-label/route-id decoupling decided
  here.
