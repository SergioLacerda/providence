---
name: {{ skill.name }}
description: {{ skill.description }}
---

# {{ skill.name }}

## Canonical sources

- `.providence/agent-instructions.md`
- `.providence/commands/registry.json`
- `.providence/skills/registry.json`
- `.providence/skills/{{ skill.name }}/skill.yaml`

## Preflight

1. Read `.providence/agent-instructions.md`.
2. Run `providence ask "$QUERY"`.
3. If `execution_gate` is `blocked`, report its reason and stop.

## Execution

Run `providence skills run {{ skill.name }}`.

## Fallback

If the local governance sources are unavailable, report the drift and use:

{% for command in skill.cli_fallback %}- `{{ command }}`
{% endfor %}
