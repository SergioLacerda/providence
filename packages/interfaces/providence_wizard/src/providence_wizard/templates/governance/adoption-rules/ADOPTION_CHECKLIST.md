# Governance Adoption Checklist

**Purpose**: Verify governance is fully adopted and operational
**User**: Project leads, DevOps engineers, AI agents
**Time**: ~10 minutes to complete

---

## Pre-Adoption Checklist

Complete this BEFORE running wizard:

- [ ] I have git initialized in my project
- [ ] I understand what my primary domain/specialization is
- [ ] I've identified who will be architect, governance, and operations lead
- [ ] I've read WIZARD_ADOPTION.md
- [ ] I'm ready to commit to governance (no option to skip this)

**Proceed if all checked** 

---

## Wizard Execution Checklist

Complete these steps during `phase-0-agent-onboarding.py`:

### Discovery Phase
- [ ] Wizard detects current project structure
- [ ] Wizard identifies available templates
- [ ] Wizard suggests seedlings based on domain

### Configuration Phase
- [ ] Set your domain name (e.g., "api-service")
- [ ] Select language/framework
- [ ] Choose enforcement level (recommended: "standard")
- [ ] Identify architect email
- [ ] Identify governance lead email
- [ ] Identify operations lead email

### Template Selection Phase
- [ ] Review suggested seedlings
- [ ] Select active seedlings (at least one)
- [ ] Customize seedling options if needed

### Validation Phase (Automatic)
- [ ] Wizard creates `.providence/` directory
- [ ] Wizard generates `metadata.json`
- [ ] Wizard creates seedling directories
- [ ] Wizard validates JSON syntax
- [ ] Wizard creates PHASE 0 completion marker

### Completion Phase
- [ ] Review generated files
- [ ] Read suggested next steps
- [ ] Wizard exits successfully (exit code 0)

---

## Post-Wizard Verification Checklist

Complete these IMMEDIATELY after wizard finishes:

### File Verification
```bash
# Check 1: metadata.json exists and is valid JSON
[ -f .providence/metadata.json ] && echo "" || echo ""
python3 -m json.tool .providence/metadata.json > /dev/null && echo "" || echo ""

# Check 2: Seedlings directory exists
[ -d .providence/seedlings ] && echo "" || echo ""

# Check 3: At least one seedling created
[ "$(ls -1 .providence/seedlings | wc -l)" -gt 0 ] && echo "" || echo ""

# Check 4: Phases directory exists
[ -d .providence/phases ] && echo "" || echo ""
```

- [ ] All file checks pass ()

### Configuration Verification
```bash
# Check metadata.json content
python3 << 'EOF'
import json
cfg = json.load(open('.providence/metadata.json'))

# Verify structure
checks = {
    "domain": cfg.get('domain') != None,
    "authority.architect": len(cfg.get('authority', {}).get('architect', [])) > 0,
    "authority.governance": len(cfg.get('authority', {}).get('governance', [])) > 0,
    "authority.operations": len(cfg.get('authority', {}).get('operations', [])) > 0,
    "seedlings.active": len(cfg.get('seedlings', {}).get('active', [])) > 0,
    "enforcement": cfg.get('policies', {}).get('enforcement') in ['strict', 'standard', 'permissive'],
    "phase_0_completed": 0 in cfg.get('phases', {}).get('completed', [])
}

for check, result in checks.items():
    print(f"{'' if result else ''} {check}")
EOF
```

- [ ] All configuration checks pass ()

### Health Check Verification
```bash
# Run AHP to validate everything
python packages/agent_handshake.py --mode=compact
```

**Expected output**:
```
 SDD STATUS
State:  HEALTHY (or  PARTIAL)
Confidence: 70%+
```

- [ ] AHP reports HEALTHY or PARTIAL (not NOT_CONNECTED)
- [ ] Confidence score is 50%+

---

## Knowledge Verification Checklist

Complete the governance quiz:

```bash
python packages/quiz_executor.py --topic=governance
```

**Expected**:
- Pass threshold: 70%
- Questions: 3
- Topics: governance, authority, seedlings

- [ ] Quiz score  70%
- [ ] All topic questions answered

---

## Integration Verification Checklist

Verify governance integrates with existing systems:

### Git Integration
```bash
# Governance files should be committed
git status .providence/
```

- [ ] `.providence/metadata.json` is tracked in git
- [ ] `.providence/seedlings/` is tracked in git
- [ ] Files committed to main branch

### Wizard Integration
```bash
# Test wizard can see governance
python packages/interfaces/providence_wizard/src/providence_wizard/SCRIPTS/phase-0-agent-onboarding.py --validate-only
```

- [ ] Wizard recognizes existing governance
- [ ] No re-initialization needed

### CI/CD Integration
```bash
# Check GitHub Actions health check workflow
cat .github/workflows/health-check.yml | grep -A5 "governance" || echo "Add governance checks to workflow"
```

- [ ] Health check workflow references .providence/
- [ ] GitHub Actions validates governance on PR

---

## Enforcement Mode Verification Checklist

Verify enforcement level is working:

### For STRICT mode
```bash
# This should FAIL
python script.py --force --skip-checks
```

- [ ] Manual bypass is blocked
- [ ] User sees error message about enforcement

### For STANDARD mode
```bash
# This should WARN but allow
python script.py --force --skip-checks
```

- [ ] Bypass is allowed
- [ ] Warning is displayed

### For PERMISSIVE mode
```bash
# This should WARN and allow
python script.py --force --skip-checks
```

- [ ] Bypass is allowed
- [ ] Minimal warning

---

## Authority Verification Checklist

Verify governance roles are properly assigned:

```bash
# Extract authority from metadata.json
python3 << 'EOF'
import json
cfg = json.load(open('.providence/metadata.json'))
authority = cfg.get('authority', {})

for role, emails in authority.items():
    print(f"{role}: {', '.join(emails)}")
EOF
```

- [ ] Architect identified: ____________
- [ ] Governance lead identified: ____________
- [ ] Operations lead identified: ____________
- [ ] All roles assigned to valid emails

---

## Seedling Verification Checklist

Verify seedlings are properly configured:

```bash
# List active seedlings
python3 << 'EOF'
import json
cfg = json.load(open('.providence/metadata.json'))
active = cfg.get('seedlings', {}).get('active', [])
print(f"Active seedlings: {active}")

# Verify directories exist
import os
for seedling in active:
    path = f".providence/seedlings/{seedling}"
    if os.path.isdir(path):
        print(f" {seedling}")
    else:
        print(f" {seedling} (missing)")
EOF
```

- [ ] At least 1 active seedling defined
- [ ] All active seedling directories exist
- [ ] Each has governance-specialization.json

---

## Final Adoption Status

**Mark this section when all above checklists are complete:**

- [ ] Pre-Adoption Checklist: COMPLETE
- [ ] Wizard Execution Checklist: COMPLETE
- [ ] Post-Wizard Verification: COMPLETE
- [ ] Knowledge Verification: COMPLETE
- [ ] Integration Verification: COMPLETE
- [ ] Enforcement Mode Verification: COMPLETE
- [ ] Authority Verification: COMPLETE
- [ ] Seedling Verification: COMPLETE

---

## Adoption Complete! 

**Date Adopted**: ____________
**Adopted By**: ____________
**Enforcement Level**: ____________ (strict/standard/permissive)
**Primary Domain**: ____________

### Next Steps

1. **Commit governance files to git**
   ```bash
   git add .providence/
   git commit -m "chore: Initialize SDD Architecture governance"
   git push origin main
   ```

2. **Share governance details with team**
   - Authority roles and contacts
   - Active seedlings and patterns
   - Enforcement policies

3. **Start PHASE 1**
   - Create foundation code
   - Apply seedling patterns
   - Document decisions

4. **Re-verify monthly**
   - Run this checklist again
   - Update governance as needed
   - Keep quiz scores current

---

## Troubleshooting

### "Some checks are failing"
1. Re-read the failing check
2. Run the suggested command
3. Fix the issue
4. Re-check

### "I don't understand a check"
1. Find the related guide:
   - WIZARD_ADOPTION.md
   - GOVERNANCE_IMPLEMENTATION.md
   - ENFORCEMENT_GUIDE.md
   - MANDATORY_POLICIES.md

2. Or ask: "How do I fix [specific check]?"

### "Can I skip this checklist?"
No. All checks must pass for governance adoption to be considered complete.

---

**Version**: 1.0 | **Status**:  Mandatory | **Last Updated**: 2026-04-26
