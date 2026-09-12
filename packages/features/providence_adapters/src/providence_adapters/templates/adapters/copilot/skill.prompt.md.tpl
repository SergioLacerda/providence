---
description: {{ skill.description }}
---

Source: `.providence/skills/{{ skill.name }}/skill.yaml`{% if skill.skill_md is defined %} Â· `.providence/skills/{{ skill.name }}/SKILL.md`{% endif %}

Steps:
1. Read `.providence/agent-instructions.md`
2. Read `.providence/skills/registry.json`
3. Confirm skill `{{ skill.name }}` is registered
4. Execute: `{{ skill.cli_fallback[0] }}`
5. Return `policy_result` and `next_actions`

Allowed: {% for cmd in skill.allowed_tools %}`{{ cmd }}` {% endfor %}

Risk: `{{ skill.risk_score }}`

{% include "_governance_contract.md" %}
