# Quick Reference: SDD Governance

**Quick Lookup Table for AI Agents & Developers**

---

## Common Tasks

| Task | Command | Expected Output |
|------|---------|-----------------|
| Check governance status | `python packages/agent_handshake.py --mode=compact` |  HEALTHY (if adopted) |
| Initialize governance | `python packages/interfaces/providence_wizard/src/providence_wizard/SCRIPTS/phase-0-agent-onboarding.py` | Wizard walks you through setup |
| List governance policies | `cat .providence/metadata.json` | JSON config |
| Check authority roles | `grep -A5 '"authority"' .providence/metadata.json` | Lists architect, governance, ops |
| Validate compliance | `python packages/quiz_executor.py --topic=governance` | Score + topic breakdown |
| View seedlings | `ls -la .providence/seedlings/` | List of active domains |
| Update enforcement | Edit `.providence/metadata.json`  set `"enforcement": "strict"` | Blocks bypasses |

---

## File Locations

```
.providence/
 metadata.json         Main config (user edits this)
 seedlings/
    {domain}/                Domain-specific templates
        governance-specialization.json
        README.md
        implementation/
 phases/                       Phase tracking
    PHASE_0_ENTRY.json
    ...PHASE_7_DELIVERY.json
 enforcement/                  Rules & validation
     mandatory-rules.json
     adoption-checklist.json
```

---

## Health Check States

| State | Symbol | Meaning | Next Action |
|-------|--------|---------|------------|
| HEALTHY |  | Governance fully adopted | Proceed with work |
| PARTIAL |  | Governance incomplete | Complete setup steps |
| NOT_INITIALIZED |  | PHASE 0 not run | `python phase-0-agent-onboarding.py` |
| MISCONFIGURED |  | Governance files broken | Fix .providence/metadata.json |
| NOT_CONNECTED |  | No governance found | Initialize with wizard |

---

## AI Agent Decision Tree

```
User asks about governance?
 Yes, wants to ADOPT
    Send to WIZARD_ADOPTION.md
      Recommend: python packages/interfaces/providence_wizard/src/providence_wizard/SCRIPTS/phase-0-agent-onboarding.py

 Yes, wants to IMPLEMENT
    Send to GOVERNANCE_IMPLEMENTATION.md
      Show structure & step-by-step

 Yes, wants to ENFORCE
    Send to ENFORCEMENT_GUIDE.md
      Enable strict mode + manual bypass disabled

 Yes, needs QUICK_REFERENCE
     This document (you're reading it!)
```

---

## Enforcement Levels

| Level | Strictness | Bypass Allowed | Use Case |
|-------|-----------|---|---|
| `strict` |  Maximum | No | Production, critical systems |
| `standard` |  Moderate | Only by architect | Most projects |
| `permissive` |  Low | Anyone can override | Dev/experimental |

Set in `metadata.json`:
```json
"policies": {
  "enforcement": "strict"
}
```

---

## Quick Setup (5 min)

```bash
# 1. Run wizard (interactive, ~3 min)
python packages/interfaces/providence_wizard/src/providence_wizard/SCRIPTS/phase-0-agent-onboarding.py

# 2. Verify governance created
ls -la .providence/metadata.json

# 3. Validate with health check
python packages/agent_handshake.py --mode=compact

# 4. If healthy, you're done!
#  HEALTHY  ready for PHASE 1
```

---

## Error Messages & Fixes

###  "metadata.json not found"
**Fix:** Run wizard: `python packages/interfaces/providence_wizard/src/providence_wizard/SCRIPTS/phase-0-agent-onboarding.py`

###  "Governance files not valid JSON"
**Fix:** `python3 -m json.tool .providence/metadata.json` to find errors, fix them

###  "Authority not recognized"
**Fix:** Add your email to `authority` section in metadata.json

###  "Manual bypass blocked"
**Fix:** Change `"manual_bypass_allowed": true` if you need override (not recommended)

###  "Phase progression blocked"
**Fix:** Update `"phases"."current"` in metadata.json to match progress

---

## Integration Points

### With Agent Handshake Protocol (AHP)
- AHP Layer 4 validates governance compliance
- If governance enforcement="strict", AHP blocks non-compliant operations
- Semantic trigger: "governance", "policy", "compliance" keywords

### With Quiz System
- Topic: governance (3 questions)
- Tests understanding of policies, authority, seedlings
- Pass 70% to confirm knowledge

### With Wizard
- PHASE 0 creates initial governance structure
- Wizard walks through all setup steps
- Output validated by AHP

---

## Authority Roles Explained

| Role | Permission | Example |
|------|-----------|---------|
| `architect` | Modify policies, create seedlings, deploy | Jane (lead architect) |
| `governance` | Enforce rules, approve changes | Bob (governance lead) |
| `operations` | Deploy to production, manage runtime | Alice (ops engineer) |

Add users to roles in metadata.json:
```json
"authority": {
  "architect": ["jane@company.com"],
  "governance": ["bob@company.com"],
  "operations": ["alice@company.com"]
}
```

---

## Checklist: Is Governance Adopted?

- [ ] `.providence/metadata.json` exists
- [ ] `.providence/seedlings/` has at least one domain
- [ ] Authority roles assigned
- [ ] Enforcement level set (strict/standard/permissive)
- [ ] AHP reports HEALTHY status
- [ ] Quiz passes (governance topic)
- [ ] Phase 0 marked complete

If all checked: **Governance is adopted!** 

---

**Version**: 1.0 | **AI-Friendly**: Yes | **Last Updated**: 2026-04-26
