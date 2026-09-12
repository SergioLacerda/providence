---
description: {{ command.id }} command adapter
mode: agent
---

## Source

`.providence/commands/{{ command.id }}/command.yaml`

## Required behavior

1. Run preflight: `providence runtime status`
2. Validate governance: `providence governance validate`
3. Execute:
{% if command.routes_to.type == "cli" %}
   `{{ command.routes_to.command }}`
{% elif command.routes_to.type == "skill" %}
   `providence skills run {{ command.routes_to.id }}`
{% else %}
   `echo "Invalid command routes_to configuration"`
{% endif %}
4. Return `policy_result` and `next_actions`
{% if command.routes_to.note %}
## Adapter note

{{ command.routes_to.note }}
{% endif %}

{% include "_governance_contract.md" %}

## PROVIDENCE GOVERNANCE

`PROVIDENCE GOVERNANCE: drift=${status} | governance=${status} | profile={{ command.id }}`
