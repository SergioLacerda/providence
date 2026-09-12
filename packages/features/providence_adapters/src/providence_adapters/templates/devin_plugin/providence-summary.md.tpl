# Providence Governance Summary (embedded snapshot, Soft/Standalone)

Governance summary digest: `sha256:{{ governance_summary_digest }}`

Not canonical. This is a best-effort condensed snapshot compiled from the source Providence project's `.providence/source/` at generation time â€” see `metadata/provenance.json` for the exact source revision. If a mandate or guideline shows "(no summary available in source)", the canonical source itself had no description at compile time; this is a source-content gap, not a rendering bug.

## Mandates

{% for m in mandates %}
### {{ m.id }} â€” {{ m.title }}

{{ m.description if m.has_description else "(no summary available in source)" }}

{% endfor %}
## Guidelines

{% for g in guidelines %}
### {{ g.category }}

{{ g.highlight if g.has_highlight else "(no summary available in source)" }}

{% endfor %}
