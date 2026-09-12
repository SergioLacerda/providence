---
name: sdd-correct
description: Apply minimal targeted correction to a specific governance violation.
risk: medium
---

# sdd-correct

## Purpose

Apply the minimal correct fix to a single governance violation identified by `diagnose`. Operates surgically — one violation per execution. Does not make systemic changes; that is the responsibility of `convergir`.

## When to use

- `diagnose` returned one or more violations and you are addressing them one at a time
- A specific mandate non-compliance was found in a targeted check
- Governance drift on a single item needs to be resolved before proceeding

## Required protocol

1. Load `.providence/agent-instructions.md`
2. Confirm skill is registered in `.providence/skills/registry.json` as `sdd-correct`
3. Identify the single target violation from `diagnose` output
4. Apply the minimal correction to resolve the violation
5. Verify the correction: `sdd governance validate`
6. Return `correction_applied`, `violation_resolved`, and any `residual_violations`

## Allowed CLI

- `sdd governance validate`
- `sdd runtime status --force`
- `sdd doctor run`

## Output format

Return YAML with:
- `correction_applied`: description of what was corrected
- `violation_resolved`: the violation ID or description that was resolved
- `residual_violations`: list of remaining violations not yet addressed
- `policy_result`: PASS | WARN | FAIL

## Non-compliance

- Do not make systemic or structural changes — use `convergir` for that
- Do not skip governance validation after applying the correction
- Do not address multiple unrelated violations in a single pass
- Do not declare the violation resolved without running `sdd governance validate`
