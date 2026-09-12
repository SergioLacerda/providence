# Anti-Pattern: Rule Bypass

## Definition

Circumventing mandates, policies, or rules by using workarounds, hacks, or "just-this-once" exceptions instead of following the defined governance path.

---

## Symptoms

- "I know I should do X, but I'll do Y because it's faster"
- Conditional rule application ("This is an exception")
- Using `--no-verify`, `--force`, or unsafe flags to skip checks
- Commenting out validation, linting, or testing requirements
- Merging code that fails governance validation
- Modifying code paths to avoid mandate compliance

---

## Examples

- ❌ Skipping `providence governance validate` before delivery
- ❌ Disabling tests with `# pragma: no cover` when they should pass
- ❌ Hardcoding credentials instead of using environment variables (violates security mandate)
- ❌ Importing infrastructure into domain layer because "it's convenient"
- ❌ Adding `--no-gpg-sign` to commits (violates P003 Mandatory Human Review)
- ❌ Using `git push --force` to rewrite history

---

## Root Cause

- Misunderstanding rule purpose (thought it was optional/contextual)
- Time pressure ("I'll fix it later")
- Disagreement with rule (believe it's wrong)
- Not knowing the alternative path that IS compliant
- Treating governance as advisory rather than mandatory

---

## Impact

- 🔴 **CRITICAL:** Violates M003 (Context Awareness), M005 (Token Economy), M007 (Telemetry)
- 🔴 **CRITICAL:** Violates P003 (Mandatory Human Review) if bypassing human gates
- ❌ Governance fingerprint mismatches (compliance audit fails)
- ❌ Unforeseen consequences from skipped validation
- ❌ Sets precedent for others to bypass rules
- ❌ Breaks audit trail and forensics capability

---

## Prevention

1. **Understand the rule first** — Read why it exists (check ADRs, commit history, decision models)
2. **Use [EXECUTION_DECISION.md](../decision-models/EXECUTION_DECISION.md)** — Validate governance before proceeding
3. **If rule conflicts with task:** Escalate per [P003](../../policies/P003_MANDATORY_HUMAN_REVIEW.md) — get human approval BEFORE bypassing
4. **Check anti-patterns before hacking** — "Is there a compliant path?" (probably yes)
5. **Enforce via CI/CD** — Use pre-commit hooks, CI gates, branch protection (not agent-bypassed)

---

## Cure

**Immediate:**

1. **Revert** the bypass (if committed)
2. **Document** why you thought bypass was necessary
3. **Find** the compliant path (escalate to human if needed)
4. **Implement** the compliant solution
5. **Verify** `providence governance validate` passes

**Long-term:**

- If rule genuinely conflicts with valid use case → RFC (Request for Comments) to change rule
- Never make unilateral decisions about rule exceptions
- If you need a bypass → that's a signal the rule needs clarification or the process needs adjustment

---

## Related

- [P003: Mandatory Human Review](../../policies/P003_MANDATORY_HUMAN_REVIEW.md) — Escalation process
- [EXECUTION_DECISION.md](../decision-models/EXECUTION_DECISION.md) — Pre-delivery governance validation
- [M005: Token Economy](../../mandates/M005_TOKEN_ECONOMY.md) — Circuit breaker rules (cannot bypass)
- [RESOLUTION_BYPASS.md](../../../../../cognition/anti-patterns/RESOLUTION_BYPASS.md) — Specific case: dependency resolution hacking
