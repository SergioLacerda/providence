# Wizard Integration for Governance Adoption

**Audience**: AI Agents Guiding Users Through PHASE 0 Onboarding
**Purpose**: Help users adopt SDD Architecture governance via the wizard
**Status**: Optimized for Semantic Detection & Automation

---

## What is Wizard Integration?

The SDD wizard (`packages/interfaces/providence_wizard/src/providence_wizard/SCRIPTS/phase-0-agent-onboarding.py`) guides users through:
1. **Governance Structure Setup** - Initialize `.providence/` directory
2. **Policy Configuration** - Define authority rules
3. **Seedling Templates** - Select domain patterns
4. **Validation** - Ensure everything works

This document explains how to help users complete these steps.

---

##  For AI Agents: Question/Response Patterns

### Pattern 1: User Doesn't Know About Wizard

```
User: "How do I set up SDD Architecture?"
AI: "Great! The fastest way is through the wizard. Let me guide you:

1. Run this command:
   python packages/interfaces/providence_wizard/src/providence_wizard/SCRIPTS/phase-0-agent-onboarding.py

2. Answer these questions:
   - What's your domain? (e.g., 'rpg-narrative-server')
   - What's the language? (python/js/java)
   - Do you want strict governance? (yes/no)

3. The wizard will create everything:
    .providence/ directory structure
    metadata.json config
    Seedling templates
    Health checks ready to run

Then verify:
   python packages/agent_handshake.py --mode=compact"
```

### Pattern 2: User Wants to Understand Steps

```
User: "What does the wizard actually do?"
AI: "The wizard (phase-0-agent-onboarding) does 5 things:

PHASE 0a - Discovery
   Detects your current project structure
   Identifies available templates
   Suggests domain-specific seedlings

PHASE 0b - Configuration
   Creates .providence/ directory
   Generates metadata.json
   Sets up authority definitions

PHASE 0c - Template Selection
   Shows available seedlings
   Lets user customize
   Applies selections

PHASE 0d - Validation
   Runs health checks
   Verifies all files created
   Reports any issues

PHASE 0e - Documentation
   Generates README
   Shows next steps
   Links to full guides"
```

### Pattern 3: User Hits an Error

```
User: "The wizard failed at governance setup"
AI: "Let me help you fix this. The wizard validation failed.

Check these in order:
1. Is .providence/ directory writable?
   ls -la .providence/

2. Is metadata.json valid JSON?
   python3 -m json.tool .providence/metadata.json

3. Are all required fields present?
   See: adoption-rules/MANDATORY_POLICIES.md

Common fixes:
    Re-run wizard: python packages/interfaces/providence_wizard/src/providence_wizard/SCRIPTS/phase-0-agent-onboarding.py
    Manual fix: See GOVERNANCE_IMPLEMENTATION.md
    Full reset: rm -rf .providence/ && run wizard again"
```

---

##  Governance Setup Flow (For Agents)

### What the Wizard Creates

```
.providence/
 metadata.json           Authority definitions
 seedlings/                      Domain templates
    {user-domain}/
       README.md
       governance-specialization.json
       implementation/
    {other-domains}/
 phases/                         Operational phases
    PHASE_0_ENTRY.json
    PHASE_1_FOUNDATION.json
    ...PHASE_7_DELIVERY.json
 enforcement/                    Rule validation
     mandatory-rules.json
     adoption-checklist.json
```

### What Users Need to Know

**Before Running Wizard:**
- Current directory is their project root
- They have git initialized
- They understand their domain

**After Running Wizard:**
- .providence/ is fully configured
- They can run health checks
- They're ready for implementation

---

##  Integration with Agent Handshake Protocol

The wizard output is **validated by AHP** (Agent Handshake Protocol):

```python
# After wizard completes, AHP validates:
python packages/agent_handshake.py --mode=compact

Expected output:
   HEALTHY - All governance files created
   .providence/metadata.json detected
   Authority definitions valid
   Seedling structure initialized
   Ready for PHASE 1
```

If AHP shows  NOT_CONNECTED:
1. Wizard didn't complete successfully
2. Files were moved or deleted
3. Manual intervention needed

**AI Agent Action:**
Guide user to adoption-rules/ENFORCEMENT_GUIDE.md to fix.

---

##  AI Agent Responsibilities

### Before Recommending Wizard
-  Confirm user understands governance concept
-  Ask if they're starting fresh project
-  Explain 5 phases of setup (~10 min)

### During Wizard Execution
-  Explain each question
-  Suggest sensible defaults
-  Provide examples for domain naming

### After Wizard Completion
-  Run AHP to verify success
-  Show governance structure created
-  Guide to next steps (PHASE 1)

### If Problems Occur
-  Check error messages
-  Verify file permissions
-  Suggest manual fixes
-  Link to detailed guides

---

##  Related Documents

- **GOVERNANCE_IMPLEMENTATION.md** - Deep dive into each .providence/ component
- **QUICK_REFERENCE.md** - Fast lookup table
- **ENFORCEMENT_GUIDE.md** - Mandatory policies
- **packages/agent_handshake.py** - Validation engine

---

**Version**: 1.0 | **AI-Optimized**: Yes | **Last Updated**: 2026-04-26
