---
name: sdd-stabilize
description: Run stabilization checks before handoff.
risk: medium
---

# stabilize

## Purpose

Run pre-delivery quality gates (lint + CI-validate) to confirm the workspace is stable before handoff or merge. Returns pass/fail result with actionable next steps.

## When to use

- Before any PR or merge request
- Before agent handoff to a human reviewer
- After significant refactoring or dependency changes
- As part of a delivery checklist

## Required protocol

1. Load `.providence/agent-instructions.md`
2. Confirm skill is registered in `.providence/skills/registry.json` as `sdd-stabilize`
3. Run preflight: `sdd runtime status`
4. Run lint: `sdd lint run`
5. Run CI-validate: `sdd test ci-validate`
6. Return `policy_result` and `next_actions`

## Allowed CLI

- `sdd lint run`
- `sdd test ci-validate`

## Output format

Return YAML with:
- `policy_result`: PASS | FAIL | WARN
- `gate_results`: lint and ci-validate outcomes
- `next_actions`: ordered list of remediation steps if any gate fails

## Non-compliance

- Do not skip lint or ci-validate — both gates are required
- Do not report PASS if any gate fails
- Do not modify source files to force a passing result
- Escalate to human on `critical_violation` or `repeat_failure`
