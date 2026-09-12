# Providence Governance Projection for Devin

Profile: **Soft/Standalone**
Provider: `devin`
Plugin version: `{{ plugin_version }}`
Policy digest (embedded snapshot): `sha256:{{ policy_digest }}`
Source revision: `{{ source_revision }}`
Built at: `{{ built_at }}`

## Assurance disclosure

This plugin ships an embedded snapshot of Providence governance skills. It has **not** verified a live Providence connection for this session.

- `policy_source: embedded_snapshot`
- `assurance: reduced`
- `external_dependencies: none`

Soft/Standalone assurance is never equivalent to a connected Hard/Connected Providence session. Do not represent this plugin's governance as equivalent to a live-verified Providence policy.

## Precedence order

1. Provider or organization safety controls (Devin's own permissions/config).
2. Connected Providence hard policy (not active in this profile).
3. Project canonical policy (this project's own `.providence/`, if present).
4. Embedded Providence snapshot (this plugin's governance summary{% if include_skills %} and `skills/`{% endif %}).
5. Provider local rules (`.devin/config.json`, project `AGENTS.md`, `rules/`).
6. User task instructions.

## Skill discovery

{% if include_skills %}
Skills embedded in this plugin are listed under `skills/`. Each skill file documents its own allowed CLI commands and risk score. Do not invent commands beyond what a skill file declares. Each skill's allowed CLI assumes the `providence` CLI is installed in this environment â€” if it is not, treat that skill as unavailable rather than improvising an equivalent command.
{% else %}
This build does not embed the Providence skill catalog (`include_skills=False`). No `skills/` directory is present. This plugin provides governance context only (assurance disclosure, precedence order, Providence summary below) â€” it does not teach Devin any `providence`-CLI-backed operations.
{% endif %}
{% if has_coding_practices %}
See `rules/sdd-coding-practices.md` for coding anti-patterns and cures (currently: universal + Go-specific).
{% endif %}

## Providence Summary (embedded snapshot)

Governance fingerprint: `{{ governance_fingerprint }}`
Workspace version: `{{ workspace_version }}`
Mandate count: `{{ mandate_count }}`
Mandates with a source description: `{{ mandate_described_count }}/{{ mandate_count }}`
Governance summary digest: `sha256:{{ governance_summary_digest }}`

This is an index, not policy text â€” mandate IDs and titles only. Full detail (where available in the source) is in `rules/providence-summary.md`. A general, CLI-independent behavioral ruleset is in `rules/sdd-soft-governance-behavior.md`. None of these are canonical; see `metadata/provenance.json` for the source revision this was compiled from.

Mandates:
{% for m in mandates %}
- `{{ m.id }}` â€” {{ m.title }}
{% endfor %}

Guideline categories:
{% for g in guideline_categories %}
- {{ g }}
{% endfor %}

## Canonical source

This plugin is a generated projection. It is **not** the canonical governance source. Canonical Providence policy lives in the `.providence/` directory of the Providence project this plugin was compiled from â€” see `metadata/provenance.json` for the exact source revision.
