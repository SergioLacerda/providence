---
{% set item_name = skill.name if skill.name is defined else skill.id %}
{% set item_description = skill.description if skill.description is defined else item_name ~ " command adapter" %}
{% set routes_to = skill.routes_to if skill.routes_to is defined else None %}
{% set is_command = skill.id is defined and skill.name is not defined %}
name: {{ item_name }}
description: {{ item_description }}
---

## Source

- `{% if is_command %}.providence/commands/{{ item_name }}/command.yaml{% else %}.providence/skills/{{ item_name }}/skill.yaml{% endif %}`
{% if skill.skill_md is defined %}- `.providence/skills/{{ item_name }}/SKILL.md` (full protocol)
{% endif %}

## Invocation

{% if is_command %}
Use when the user invokes `/{{ item_name }}`.
{% else %}
Use when:
{% for t in skill.when_to_use %}
- {{ t }}
{% endfor %}
{% endif %}

## Required steps

1. Load `.providence/agent-instructions.md`
2. Load `{% if is_command %}.providence/commands/registry.json{% else %}.providence/skills/registry.json{% endif %}`
3. Confirm {% if is_command %}command{% else %}skill{% endif %} `{{ item_name }}` is registered
4. Follow the SDD {% if is_command %}command{% else %}skill{% endif %} protocol
5. Use only allowed CLI
{% if is_command %}
6. Execute:
{% if routes_to and routes_to.type == "cli" %}
   `{{ routes_to.command }}`
{% elif routes_to and routes_to.type == "skill" %}
   `providence skills run {{ routes_to.id }}`
{% else %}
   `echo "Invalid command routes_to configuration"`
{% endif %}
{% endif %}

{% include "_governance_contract.md" %}

## Allowed CLI

{% if is_command %}
{% if routes_to and routes_to.type == "cli" %}
- `{{ routes_to.command }}`
{% elif routes_to and routes_to.type == "skill" %}
- `providence skills run {{ routes_to.id }}`
{% else %}
- see `.providence/commands/{{ item_name }}/command.yaml`
{% endif %}
{% else %}
{% for cmd in skill.allowed_tools %}
- `{{ cmd }}`
{% endfor %}
{% endif %}

## Risk

`{{ skill.risk_score if skill.risk_score is defined else "controlled" }}`
