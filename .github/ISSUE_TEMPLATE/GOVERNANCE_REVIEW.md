---
name: Governance Review
about: Request governance review for changes
title: "[GOVERNANCE] "
labels: governance-review
assignees: ''

---

## 📋 Governance Review Checklist

**Mandatory Policy Compliance:**

- [ ] governance-core.json exists and valid
- [ ] JSON format is valid (no parse errors)
- [ ] Active seedling is defined
- [ ] Authority roles are assigned
- [ ] Enforcement level is set (STRICT/STANDARD/PERMISSIVE)
- [ ] PHASE 0 (onboarding) completed
- [ ] Health check passes (10/10)

**Code Quality:**

- [ ] Type hints on all functions
- [ ] Docstrings on classes/methods
- [ ] Error handling with try/except
- [ ] No hardcoded values (use config)
- [ ] Logging instead of print()
- [ ] Tests included

**Performance:**

- [ ] Health check target met (<200ms quick, <1s full)
- [ ] Governance validation target met (<500ms)
- [ ] Agent handshake target met (<2s)
- [ ] Benchmarked: `python3 tests/performance/benchmark.py`

## 🔍 Violation Details

**If violations found:**

1. **Policy violated**: [Which of the 7 mandatory policies]
2. **Why it violated**: [Explanation]
3. **Impact**: [What breaks or degrades]
4. **Fix proposed**: [How to fix it]

## ✅ Verification

**Verify with:**

```bash
# Check compliance
python3 packages/tools/governance_compliance.py --verify

# Get fix steps
python3 packages/tools/governance_compliance.py --fix-steps

# Check enforcement
python3 packages/tools/governance_compliance.py --enforcement-check
```

## 📞 Reviewer

**Who should review?**
- `architect` - Final authority on governance policies
- `governance` - Day-to-day compliance
- `operations` - Runtime enforcement

## 📚 Related Docs

- [MANDATORY_POLICIES.md](../../packages/.providence-wizard/templates/governance/adoption-rules/MANDATORY_POLICIES.md)
- [ENFORCEMENT_GUIDE.md](../../packages/.providence-wizard/templates/governance/adoption-rules/ENFORCEMENT_GUIDE.md)
- [Governance Implementation](../../packages/.providence-wizard/templates/governance/base-seedling/GOVERNANCE_IMPLEMENTATION.md)

---

**Reviewers**:
1. Verify compliance: `python3 packages/tools/governance_compliance.py --verify`
2. Check proposed fix: `python3 packages/tools/governance_compliance.py --fix-steps`
3. Approve with label: `governance-approved`
