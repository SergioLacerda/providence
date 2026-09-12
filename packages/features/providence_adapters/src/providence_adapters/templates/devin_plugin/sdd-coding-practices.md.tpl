# SDD Coding Practices (Go pilot)

Coding practices digest: `sha256:{{ coding_practices_digest }}`

Not canonical â€” parsed from this source project's `docs/cognition/anti-patterns/` at generation time. Currently covers all 5 universal anti-patterns plus Go-specific guidance for one of them (dependency resolution). Other languages are not yet covered â€” see `metadata/provenance.json` for the source revision.

{% for ap in anti_patterns %}
## {{ ap.title }}

**Problem:** {{ ap.problem }}

**Cure:** {{ ap.cure }}

**Benchmark:** {{ ap.benchmark }}
{% if ap.has_symptoms %}
**Symptoms:** {{ ap.symptoms }}
{% endif %}
{% if ap.has_danger %}
**Why it's dangerous:** {{ ap.danger }}
{% endif %}

{% endfor %}
## Go-Specific Guidance â€” Dependency Resolution

**Hacks to avoid:**

{{ go_resolution_bypass.hacks }}

**Cures:**

{{ go_resolution_bypass.cures }}

{% if go_resolution_bypass.detection %}
**Detection:**

{{ go_resolution_bypass.detection }}
{% endif %}

**Rule:** {{ go_resolution_bypass.rule }}
