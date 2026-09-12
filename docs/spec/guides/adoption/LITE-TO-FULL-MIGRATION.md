# 🔄 LITE → FULL Migration Guide

**Purpose:** Upgrade from LITE to FULL governance when team is ready
**Time Required:** 30 minutes
**Difficulty:** Low (mostly configuration)

---

## When to Upgrade

### ✅ Ready for FULL if

- Team is comfortable with 10 LITE principles
- Built 1-2 features using LITE successfully
- Project growing (code > 500 lines)
- Multiple developers need coordination
- Production deployment planned
- Need comprehensive compliance
- Team wants CI/CD to enforce all rules

### ⏳ Not yet ready if

- Still learning SDD concepts (stay LITE)
- Project is experimental/temporary
- Team < 2 people
- Code still < 100 lines

---

## Step-by-Step Migration (30 min)

### Phase 1: Prepare (5 min)

```bash
# 1. Backup current configuration
cp -r .providence/ .ai-backup-lite/
cp .pre-commit-config.yaml .pre-commit-config-lite.yaml

# 2. Create FULL branch
git checkout -b upgrade/lite-to-full
```

### Phase 2: Update Constitution (5 min)

**Add 5 Enterprise Principles:**

```bash
# Edit: EXECUTION/spec/CANONICAL/rules/constitution.md

# Add these principles after the existing 10:
11. Technology Stack Immutable
12. Data Governance
13. Security by Default
14. Performance as Requirement
15. Operational Excellence
```

**Constitution now covers:**

- Core: Clean Architecture, Async, Ports, ADRs, Governance ✅
- Quality: Framework Bleed, Types, Tests, Docs, Autonomy ✅
- Enterprise: Tech Stack, Data, Security, Performance, Ops 🆕

### Phase 3: Extend Rules (5 min)

**Enable 11 Additional Rules:**

```bash
# From: 5 LITE rules
# To: 16 FULL rules

# New rules focus on:
- Enterprise compliance (tech stack immutable)
- Security (auth, encryption, audit trails)
- Performance (response times, optimization)
- Operations (runbooks, incident response)
```

Update `.providence/constitution.yaml`:

```yaml
# Old LITE rules (keep)
rules:
  - layer_validation
  - async_compliance
  - port_contracts
  - type_hints
  - adr_logging

# Add new FULL rules
  - technology_stack_immutable
  - no_circular_imports
  - no_print_statements
  - error_mapping_required
  - sensitive_data_protection
  - performance_testing_required
  - runbook_maintenance
  - incident_response_required
  - security_by_default
  - data_governance
  - operational_excellence
```

### Phase 4: Upgrade Pre-commit Hooks (5 min)

```bash
# Old (LITE): 5 hooks
# New (FULL): 12 hooks

# Run upgrade script
./scripts/upgrade-precommit-lite-to-full.sh

# Verify new hooks
grep -c "id:" .pre-commit-config.yaml
# Should output: 12 (was 5)
```

### Phase 5: Set Up Comprehensive Tests (5 min)

```bash
# Create full test suite
pytest tests/full/ --cov

# Expected results:
# - Architecture tests: PASS
# - Compliance tests: PASS
# - Performance tests: PASS
# - Security tests: PASS

# Add CI/CD pipeline
cp .github/workflows/sdd-lite.yml .github/workflows/sdd-full.yml
```

### Phase 6: Validate Migration (3 min)

```bash
# Run validation checklist
python EXECUTION/tools/validate-migration.py --from=lite --to=full

# Should output:
# ✅ Constitution updated (15 principles)
# ✅ Rules enabled (16 rules)
# ✅ Pre-commit hooks (12 hooks)
# ✅ Tests configured (45 DoD criteria)
# ✅ CI/CD pipeline ready
# ✅ Ready for production
```

### Phase 7: Commit & Deploy (2 min)

```bash
git add -A
git commit -m "chore: upgrade from LITE to FULL governance

- Extended constitution: 10 → 15 principles
- Enabled 11 additional rules for production
- Pre-commit hooks: 5 → 12 checks
- Full test suite with 45 DoD criteria
- CI/CD compliance pipeline ready

Closes #XXX"

git push origin upgrade/lite-to-full
```

---

## What Changes

### Constitution

```diff
- 10 core principles
+ 5 enterprise principles
= 15 total (immutable)
```

### Rules

```diff
- 5 essential rules (layer, async, ports, types, ADR)
+ 11 additional rules (stack, circular, print, errors, security, etc.)
= 16 total (mandatory)
```

### Tests

```diff
- 10 DoD criteria (architecture + testing basics)
+ 35 additional criteria (security, performance, operations, process)
= 45 total (comprehensive)
```

### Workflow

```diff
- 3 phases (Domain, Adapter, UseCase)
+ 4 additional phases (Integration, API, Compliance, Deployment)
= 7 total (full lifecycle)
```

### Pre-commit

```diff
- 5 hooks (layer, async, types, adr, imports)
+ 7 additional hooks (security, performance, lint, format, etc.)
= 12 total (strict)
```

---

## Team Communication

### Notify Team

```markdown
## 🚀 Upgrading to Providence FULL

We're upgrading governance to comprehensive level. Here's what changes:

**For You:**
- More rules enforced (good for quality, less ambiguity)
- More pre-commit checks (catches issues earlier)
- Stricter DoD criteria (fewer bugs in production)
- 7-phase workflow (clear process from start to finish)

**Timeline:**
- Today: Infrastructure updated
- Tomorrow: First feature with FULL rules
- Next week: All projects transitioned

**Questions?**
→ See [LITE to FULL Migration Guide](./LITE-TO-FULL-MIGRATION.md)
→ Ask in #sdd-governance channel
```

---

## Rollback Plan

If something breaks:

```bash
# Revert to LITE (fast rollback)
git revert <commit-hash>

# Or restore from backup
cp -r .ai-backup-lite/ .providence/
cp .pre-commit-config-lite.yaml .pre-commit-config.yaml

# Reinit pre-commit
pre-commit install
```

---

## Validation Checklist

- [ ] Constitution has 15 principles (not 10)
- [ ] Rules file has 16 items (not 5)
- [ ] Pre-commit hooks: 12 (not 5)
- [ ] Test suite runs with 45 DoD criteria
- [ ] CI/CD pipeline green
- [ ] Documentation updated
- [ ] Team trained on new workflow
- [ ] First feature completed with FULL rules

---

## Expected Timeline

| Step | Time | What Happens |
|------|------|--------------|
| Phase 1 | 5 min | Backup config |
| Phase 2 | 5 min | Constitution extended |
| Phase 3 | 5 min | Rules activated |
| Phase 4 | 5 min | Pre-commit updated |
| Phase 5 | 5 min | Tests configured |
| Phase 6 | 3 min | Validation passed |
| Phase 7 | 2 min | Committed & deployed |
| **TOTAL** | **30 min** | Ready for FULL |

---

## After Migration

### What's Better

✅ Stronger architecture enforcement
✅ Fewer bugs in production
✅ Clearer process for everyone
✅ Better compliance tracking
✅ Easier onboarding with explicit rules

### What's Different

⚠️ More pre-commit checks (slower local commits, but faster CI)
⚠️ More DoD criteria (fewer "almost done" PRs)
⚠️ Stricter rules (less ambiguity = better, but less flexibility)

### New Capabilities

🎯 Full AI agent autonomy (all rules explicit)
🎯 Audit trail (every decision documented)
🎯 Performance tracking (metrics in v2.2)
🎯 Security by default (encryption, validation, auth)

---

## Troubleshooting

### Problem: Pre-commit hooks failing

```bash
# Update hooks
pre-commit autoupdate

# Run manually
pre-commit run --all-files

# If still broken, check configuration
cat .pre-commit-config.yaml | grep -A5 "python"
```

### Problem: Tests failing

```bash
# Run full test suite
pytest tests/full/ -v

# Check specific category
pytest tests/full/architecture/ -v

# Generate report
pytest tests/full/ --cov --cov-report=html
```

### Problem: CI/CD pipeline red

```bash
# Check workflow file
cat .github/workflows/sdd-full.yml

# Run locally
act push --job sdd-compliance

# Debug output
act -v
```

---

## Questions?

- **About LITE/FULL?** → [LITE-ADOPTION.md](./LITE-ADOPTION.md) / [FULL-ADOPTION.md](./FULL-ADOPTION.md)
- **About rules?** → [Rules Reference](../../canonical/core/rules/INDEX.md)
- **About workflow?** → [CORE__START_HERE.md](../operational/CORE__START_HERE.md)
- **Emergency?** → [Troubleshooting](../operational/TROUBLESHOOTING_SPEC_VIOLATIONS.md)

---

## Next Steps

1. ✅ Follow 30-minute migration plan above
2. ✅ Run validation checklist
3. ✅ Communicate with team
4. ✅ Start next feature with FULL rules
5. ✅ Provide feedback → shapes v2.2

---

**Ready to go FULL?** Let's do it! 🚀

*Framework under active development. Your experience matters.*
