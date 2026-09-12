# 🎯 PHASE 0 Flow — Agent-Driven Workspace Initialization

**Purpose:** Document the complete PHASE 0 workflow
**Audience:** Developers, team leads, agents
**Version:** SPEC v2.1

---

## 📋 Overview: Three States

### State 1: New Project (Seed Only)

When a project is first created or cloned:

```
project-alvo/
├── .spec.config              ← SEED (minimal config)
├── .github/copilot-instructions.md (references PHASE 0)
├── .vscode/ai-rules.md       (references PHASE 0)
├── .cursor/rules/spec.mdc    (references PHASE 0)
├── tests/unit/specs_ia_units/     (minimal template)
└── ... (rest of project code)

# NO .providence/context-aware/ yet (will be created by agent)
```

**Why minimal?** Project is "dumb" about SDD. Agent creates structure.

---

### State 2: Agent Starts (PHASE 0 Execution)

Agent reads instructions and executes PHASE 0:

```bash
# 1. Agent reads entry point
cat .github/copilot-instructions.md

# 2. Agent sees: "Read .spec.config first"
cat .spec.config

# 3. Agent sees: "Execute PHASE 0"
SPEC_PATH=$(grep spec_path .spec.config | cut -d' ' -f3)
cat $SPEC_PATHdocs/spec/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md

# 4. Agent executes PHASE 0 (either manually or automated)
# Option A: Manual (follow 6 steps in guide)
# Option B: Automated (run script)
python $SPEC_PATHdocs/spec/SCRIPTS/phase-0-agent-onboarding.py
```

---

### State 3: Workspace Ready (PHASE 0 Complete)

After agent completes PHASE 0:

```
project-alvo/
├── .spec.config              ← SEED
├── .providence/context-aware/        ← CREATED BY AGENT
│   ├── README.md
│   ├── task-progress/
│   │   ├── _current.md      ← Agent's tasks go here
│   │   └── completed/
│   ├── analysis/
│   │   └── _current-issues.md
│   └── runtime-state/
│       └── _current.md
├── .github/copilot-instructions.md
├── ... (rest of project)
└── (git shows new files ready to commit)
```

**Why created by agent?** Agent owns the context, learns SDD doing it.

---

## 🔄 PHASE 0 Workflow (Step-by-Step)

### For Agents: Manual Path

```
Step 1: Read .spec.config
  └─ Discovers spec_path = ../spec-architecture

Step 2: Read PHASE-0 Guide
  └─ SPEC_PATH=$(grep spec_path .spec.config | cut -d' ' -f3)
     cat $SPEC_PATHdocs/spec/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md

Step 3: Create Directories
  └─ mkdir -p .providence/context-aware/{task-progress/completed,analysis,runtime-state}

Step 4: Copy Templates
  └─ cp $SPEC_PATH/templates/ai/context-aware/* .providence/context-aware/

Step 5: Read Documentation
  └─ Read ia-rules.md
     Read context-aware-agent-pattern.md
     Take VALIDATION_QUIZ

Step 6: Validate Knowledge
  └─ Score ≥ 4/5 on quiz = PASS

Step 7: Commit
  └─ git add .providence/
     git commit -m "🚀 PHASE 0: Agent workspace initialized"
```

**Time:** ~20-30 minutes
**Result:** Workspace ready for real work

---

### For Agents: Automated Path

```bash
# Single command (does all steps)
python $(grep spec_path .spec.config | cut -d' ' -f3)docs/spec/SCRIPTS/phase-0-agent-onboarding.py
```

**What script does:**

1. ✅ Verifies .spec.config
2. ✅ Verifies SPEC framework
3. ✅ Creates directories
4. ✅ Copies templates
5. ✅ Validates knowledge (quiz)
6. ✅ Prints success report

**Time:** ~15-20 minutes
**Result:** Same workspace ready

---

## 📊 Comparison: Old vs New

### Old Approach (Manual Setup)

```
Problem:
  - Each project had .providence/context-aware/ pre-created
  - Duplicated across projects
  - Agent didn't "learn" by creating
  - Setup was implicit, not explicit

Result:
  - Knowledge scattered
  - No consistency
  - Hard to scale
```

### New Approach (Agent-Driven PHASE 0)

```
Benefit:
  ✅ Each project starts minimal
  ✅ Agent creates infrastructure explicitly
  ✅ Agent learns SDD by doing it
  ✅ Setup is repeatable, consistent
  ✅ Scales to unlimited projects

Result:
  ✅ Knowledge centralized (spec-architecture)
  ✅ Projects are "dumb" (can be cloned anywhere)
  ✅ Agents are "smart" (know how to bootstrap)
```

---

## 🎯 PHASE 0 Success Criteria

Agent has completed PHASE 0 if:

```
✅ .spec.config verified
   └─ Points to valid SPEC framework

✅ SPEC framework accessible
   └─ All required directories present

✅ .providence/context-aware/ created
   └─ All folders and templates in place

✅ Knowledge validated
   └─ Passed SDD quiz (≥4/5)

✅ Infrastructure committed
   └─ "🚀 PHASE 0" commit in git log

✅ Ready for AGENT_HARNESS
   └─ Can proceed to phases 1-7
```

---

## 📝 Example: First-Time Agent

### Day 1: Agent Joins Project

```
Agent: "I'm assigned to [PROJECT_NAME]"

Agent reads: .github/copilot-instructions.md
  → "Check .spec.config first"

Agent reads: .spec.config
  → "spec_path = ../spec-architecture"

Agent navigates to spec-architecture
  → "Ah! This is the source of truth"

Agent reads: PHASE-0-AGENT-ONBOARDING.md
  → "I need to create .providence/context-aware/"

Agent executes:
  $ python docs/ia/SCRIPTS/phase-0-agent-onboarding.py

Agent sees: "✅ PHASE 0 Complete"

Agent commits:
  $ git add .providence/ && git commit -m "🚀 PHASE 0: Agent workspace initialized"

Agent checks: .providence/context-aware/ now exists
  → task-progress/_current.md (ready to fill)
  → analysis/_current-issues.md (ready to fill)
  → runtime-state/_current.md (ready to fill)

Agent thinks: "I understand the structure now"

Agent proceeds: Read AGENT_HARNESS.md (phases 1-7)
```

**Time elapsed:** 30 minutes
**Knowledge gained:** Understands SDD, context-aware, project structure
**Confidence:** Ready to work! ✅

---

## 🔗 How PHASE 0 Connects to Everything

```
.spec.config (seed)
    ↓
    Discovers SPEC framework
    ↓
PHASE-0-AGENT-ONBOARDING.md (in spec)
    ↓
    Creates .providence/context-aware/
    ↓
Copies templates (from spec)
    ↓
Agent learns SDD (quiz + reading)
    ↓
PHASE 1-7: AGENT_HARNESS
    ↓
Real work begins! 🚀
```

---

## 📚 Files Involved

**In spec-architecture:**

- `docs/ia/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md` — Manual guide
- `docs/ia/SCRIPTS/phase-0-agent-onboarding.py` — Automated script
- `templates/ai/context-aware/` — Templates to copy

**In project (minimal):**

- `.spec.config` — Seed configuration
- `.github/copilot-instructions.md` — References PHASE 0

**Created during PHASE 0 (by agent):**

- `.providence/context-aware/` — Entire infrastructure

---

## ✅ Validation Checklist

**For project owners:**

- [ ] Project has `.spec.config` ✅
- [ ] `.spec.config` points to valid SPEC framework ✅
- [ ] `.github/copilot-instructions.md` references PHASE 0 ✅
- [ ] PHASE-0 guide exists in spec ✅
- [ ] Script exists: `phase-0-agent-onboarding.py` ✅
- [ ] Templates exist in `templates/ai/context-aware/` ✅

**For agents (before starting work):**

- [ ] Executed PHASE 0 (manual or automated) ✅
- [ ] `.providence/context-aware/` created ✅
- [ ] Passed SDD validation quiz (≥4/5) ✅
- [ ] Changes committed to git ✅
- [ ] Ready to read AGENT_HARNESS ✅

---

## 🚀 Summary

**PHASE 0 is the bridge between:**

- General SPEC framework (in spec-architecture)
- Project-specific context (in .providence/context-aware/)

**Agent executes it once per project** → Workspace is initialized and ready.

**Result:** Scalable, repeatable, agent-driven onboarding! ✅
