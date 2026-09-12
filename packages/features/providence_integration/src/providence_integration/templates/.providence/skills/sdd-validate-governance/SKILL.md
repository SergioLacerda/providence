---
name: sdd-validate-governance
description: Validate governance integrity and runtime preflight.
risk: medium
---

# validate-governance

## Purpose

Validate the integrity of compiled governance artifacts and run the full runtime preflight check. Confirms that the workspace governance is consistent, fingerprints are valid, and all required artifacts are accessible.

## When to use

- After running `sdd governance compile`
- When governance drift is suspected
- Before starting a high-risk task that requires governance assurance
- As part of CI/CD pipeline validation

## Required protocol

1. Load `.providence/agent-instructions.md`
2. Confirm skill is registered in `.providence/skills/registry.json` as `sdd-validate-governance`
3. Run preflight: `sdd runtime status`
4. Run full validation: `sdd governance validate`
5. Check fingerprints and artifact consistency
6. Return `policy_result` and `next_actions`

## Allowed CLI

- `sdd governance validate`
- `sdd runtime status`

## Output format

Return YAML with:
- `policy_result`: PASS | FAIL | WARN
- `checks`: list of validation checks with pass/fail status
- `fingerprint_valid`: boolean
- `next_actions`: ordered list of remediation steps if validation fails

## Non-compliance

- Do not report PASS if any validation check fails
- Do not skip fingerprint validation
- Run `sdd governance compile` if artifacts are missing, then re-validate
- Escalate to human on `critical_violation`
