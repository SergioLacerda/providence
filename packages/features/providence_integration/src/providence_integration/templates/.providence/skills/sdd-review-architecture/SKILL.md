---
name: sdd-review-architecture
description: Review architecture adherence against SDD mandates.
risk: high
---

# review-architecture

## Purpose

Audit the workspace architecture against SDD mandates and governance policies. Identifies violations, drift, and areas of non-compliance. High-risk skill — does not modify files but produces authoritative findings that may require human decision.

## When to use

- Before a major refactor or architectural change
- When architecture drift is suspected
- As part of a formal architecture review cycle
- When SDD governance score drops below threshold

## Required protocol

1. Load `.providence/agent-instructions.md`
2. Confirm skill is registered in `.providence/skills/registry.json` as `sdd-review-architecture`
3. Run preflight: `sdd runtime status`
4. Run governance score: `sdd governance score --verbose`
5. Cross-reference findings against `.providence/source/governance-core.json`
6. Return `policy_result` and `next_actions`

## Allowed CLI

- `sdd governance score --verbose`

## Output format

Return YAML with:
- `policy_result`: PASS | FAIL | WARN
- `violations`: list of mandate violations with severity
- `score`: numeric governance score
- `next_actions`: ordered list of corrective actions

## Non-compliance

- Do not recommend architectural changes without mandate evidence
- Do not bypass governance score — it is the authoritative source
- Escalate to human on `critical_violation` or `high_risk_change`
- This is a high-risk skill: findings must be reviewed by a human before acting
