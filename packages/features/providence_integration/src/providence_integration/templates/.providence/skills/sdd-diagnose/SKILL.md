---
name: sdd-diagnose
description: Diagnose runtime/workspace problems with governed checks.
risk: low
---

# diagnose

## Purpose

Identify and explain runtime or workspace problems using SDD governed diagnostic checks. Returns a structured report with findings and next actions without modifying any workspace state.

## When to use

- Failing checks or CI pipeline errors with unclear root cause
- Unknown runtime failures or unexpected agent behavior
- Before escalating an issue to a human reviewer
- After a governance drift is detected

## Required protocol

1. Load `.providence/agent-instructions.md`
2. Confirm skill is registered in `.providence/skills/registry.json` as `sdd-diagnose`
3. Run preflight: `sdd runtime status`
4. Execute: `sdd doctor run`
5. Return `policy_result` and `next_actions` as structured output

## Allowed CLI

- `sdd doctor run`
- `sdd runtime status`

## Output format

Return YAML with:
- `policy_result`: PASS | FAIL | WARN
- `findings`: list of issues found
- `next_actions`: ordered list of remediation steps

## Non-compliance

- Do not modify workspace files or configuration
- Do not invent diagnostic results not produced by allowed CLI
- Do not skip the preflight check
- Declare degraded mode if `.providence/skills/registry.json` is unavailable
