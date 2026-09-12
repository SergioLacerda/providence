---
description: {{ skill.description }}. Use when: {% for t in skill.when_to_use %}{{ t }}{% if not loop.last %}, {% endif %}{% endfor %}.
mode: agent
---

## Source

`.providence/skills/{{ skill.name }}/skill.yaml`{% if skill.skill_md is defined %} Â· `.providence/skills/{{ skill.name }}/SKILL.md`{% endif %}

## Required behavior

1. Run preflight: `providence runtime status`
2. Validate governance: `providence governance validate`
{% if skill.category in ["analysis", "governance"] %}
3. For large inputs: `providence organize "$QUERY"` before proceeding
{% endif %}
4. Execute: `{{ skill.cli_fallback[0] }}`
5. Return `policy_result` and `next_actions`

## Allowed CLI

{% for cmd in skill.allowed_tools %}
- `{{ cmd }}`
{% endfor %}
{% if skill.skill_md is defined %}

## Non-compliance

- Do not invent SDD commands not listed above
- Do not skip preflight or governance validate
- Declare degraded mode if `.providence/skills/registry.json` is unavailable
- See `.providence/skills/{{ skill.name }}/SKILL.md` for complete non-compliance rules
{% endif %}

{% include "_governance_contract.md" %}

## PROVIDENCE GOVERNANCE

`PROVIDENCE GOVERNANCE: drift=${status} | governance=${status} | profile={{ skill.name }}`

Agents must prefer `.providence/source/*` for governance context over compiled artifacts.
