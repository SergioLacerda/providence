---
name: {{ name }}
description: {{ description }}
risk: {{ risk_score }}
schema_version: "1.1.0"
---

# {{ name }}

## Purpose

{{ description }}

## When to use

- {{ when_to_use_0 }}

## Triggers

<!-- List keywords that should route to this skill -->
- (fill in)

## Forbidden actions

<!-- List actions this skill must never perform -->
- (fill in)

## Required protocol

1. Load `.providence/agent-instructions.md`
2. Confirm skill is registered in `.providence/skills/registry.json` as `{{ name }}`
3. Validate execution_contract is present before proceeding
4. Run preflight: `sdd runtime status`
5. Check circuit breaker state for this skill
6. Execute: `sdd runtime status`
7. Return `policy_result` and `next_actions` conforming to `skill_output` schema

## Allowed CLI

- `sdd runtime status`

## Output format

Return YAML conforming to `.providence/skills/contracts/skill_output.schema.yaml`:
```yaml
status: ok | error | degraded
result:
  policy_result: PASS | FAIL | WARN
  next_actions: []
confidence:
  overall: 0.0-1.0
error: null  # present only if status: error
next_skill: null
```

## Fallback

- `fallback_to: null` — set in `skill.yaml` if a fallback skill exists

## Non-compliance

- Do not invent SDD commands not listed in Allowed CLI
- Do not skip the preflight check
- Do not execute without a valid execution_contract
- Declare degraded mode if `.providence/skills/registry.json` is unavailable
