---
name: sdd-converge
description: Drive systemic alignment toward spec target after targeted corrections.
risk: high
---

# sdd-converge

## Purpose

Assess and drive the workspace toward systemic alignment with the governance spec. Operates at the strategic level — evaluates the overall delta between current state and target spec, produces a convergence plan, and may invoke `sdd-correct` iteratively for individual violations within that plan.

## When to use

- After one or more `sdd-correct` passes, residual delta remains
- A pattern of drift is detected across multiple areas (not a single violation)
- Spec alignment score is below threshold
- `diagnose` or `review-architecture` returned a systemic divergence

## Required protocol

1. Load `.providence/agent-instructions.md`
2. Confirm skill is registered in `.providence/skills/registry.json` as `sdd-converge`
3. Query current governance state: `sdd ask "current alignment delta"`
4. Assess the full delta: what diverges from the spec target?
5. Score alignment: estimate `alignment_score` (0.0–1.0)
6. Build `convergence_plan`: ordered list of corrections to reach alignment
7. For each item in plan: invoke `sdd-correct` or flag for human review
8. Re-assess after each correction: update `alignment_score`
9. Validate when done: `sdd governance validate`
10. Return `alignment_score`, `convergence_plan`, `delta_report`, `next_corrigir_targets`

## Allowed CLI

- `sdd ask`
- `sdd governance validate`
- `sdd runtime status --force`
- `sdd doctor run`

## Output format

Return YAML with:
- `alignment_score`: float 0.0–1.0 (1.0 = fully aligned)
- `convergence_plan`: ordered list of corrections with priority and target
- `delta_report`: summary of gaps between current state and spec
- `next_corrigir_targets`: remaining violations to be addressed by `sdd-correct`
- `policy_result`: PASS | WARN | FAIL | BLOCKED

## Non-compliance

- Do not declare convergence without running `sdd governance validate`
- Do not make structural changes without `review-architecture` gate (strict mode)
- Do not violate mandates in the process of converging toward the spec
- Do not skip `alignment_score` in the output — it is required for traceability
- Do not invoke `sdd-converge` for a single isolated violation — use `sdd-correct` instead
