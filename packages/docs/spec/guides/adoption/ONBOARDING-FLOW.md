# 🎯 SDD Onboarding Flow — Visual Guide

**Complete journey from "new user" to "executing features" with LITE or FULL**

---

## 📍 Entry Points

```
┌─────────────────────────────────────────────────────┐
│         WHERE DO YOU START?                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1️⃣ Public-facing info?                            │
│     → README.md (root)                              │
│                                                     │
│  2️⃣ Adding a NEW project?                          │
│     → INTEGRATION/README.md                         │
│                                                     │
│  3️⃣ Implementing features?                         │
│     → EXECUTION/_START_HERE.md                      │
│                                                     │
│  4️⃣ Just learning SDD?                             │
│     → adoption/INDEX.md (you are here)              │
│                                                     │
│  5️⃣ Machine (AI agent)?                            │
│     → .ai-index.md (root)                           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 Flow 1: New User Learning SDD

```
┌──────────────────────────────────────────────────────────┐
│ 1. README.md (root)                                      │
│    - What is SDD?                                        │
│    - ✨ Key Features                                     │
│    - 🎯 Step 0: Choose Your Adoption Path               │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────────┐
│ 2. LITE or FULL? (adoption/INDEX.md)                     │
│    - Comparison table                                    │
│    - Decision tree                                       │
│    - Scenarios                                           │
└────────────────────┬─────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ↓ LITE                  ↓ FULL
    ┌─────────┐            ┌──────────┐
    │ 15 min  │            │ 40 min   │
    │ Setup   │            │ Setup    │
    └────┬────┘            └────┬─────┘
         │                      │
         ├──────────┬───────────┤
         │          │           │
         ↓          ↓           ↓
    LITE-ADOPTION  INDEX  FULL-ADOPTION
    (read it)  (comparing)  (read it)
         │          │           │
         └──────────┴───────────┘
                    │
                    ↓
            ✅ ADOPTION CHOSEN
```

---

## 🎯 Flow 2: Adding New Project to SDD

```
┌──────────────────────────────────────────────────────────┐
│ 1. README.md (root)                                      │
│    "Are you adding a NEW project?"                       │
│    → INTEGRATION/README.md                               │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────↓─────────────────────────────────────┐
│ 2. INTEGRATION/README.md                                 │
│    - Phase 1: Technical setup (STEPS 1-5, same for all)  │
│    - Phase 2: Intention detection (STEP 6, choose level) │
└────────────────────┬─────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    STEP 1-5               STEP 1-5
    Setup                  Setup
    (everyone)             (everyone)
         │                       │
         └───────────┬───────────┘
                     │
            Technical setup complete
                     │
┌────────────────────↓─────────────────────────────────────┐
│ 3. INTEGRATION/STEP_6.md                                 │
│    "Detect Your Intention"                               │
│    Answer 5 questions:                                   │
│    - Team size? - Project type?                          │
│    - Compliance? - AI agents? - Error cost?              │
└────────────────────┬─────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    Mostly A's             Mostly C's
    (or edge)
         │                       │
    Choose LITE            Choose FULL
    (5 rules)              (16 rules)
         │                       │
         └───────────┬───────────┘
                     │
        Update .spec.config:
        adoption_level = lite (or full)
                     │
            ✅ PROJECT INTEGRATED
            (with intention documented)
```

---

## 🎯 Flow 3: Implementing Features (After Setup)

```
┌──────────────────────────────────────────────────────────┐
│ 1. EXECUTION/_START_HERE.md                              │
│    "What are you doing?"                                 │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ↓
         ┌───────────────────────┐
         │  🎯 STEP 0: Choose    │
         │  LITE or FULL? ✅     │
         │  (already done)       │
         └───────────┬───────────┘
                     │
            Confirm adoption level
                     │
         ┌───────────┴────────────┐
         │                        │
    1️⃣ First time?         2️⃣ Implement now?
         │                        │
         ↓                        ↓
    PHASE_0_SETUP           AGENT_HARNESS
    (20-30 min)             (7 phases)
         │                        │
         ├────────────┬───────────┤
         │            │           │
    LITE setup   Choose level  FULL workflow
    5 rules      + PATH        16 rules
    10 DoD        (A-D)        45 DoD
         │            │           │
         └────────────┴───────────┘
                     │
                     ↓
            ✅ FEATURE IMPLEMENTED
            (with appropriate governance)
```

---

## 🔄 LITE → FULL Migration

```
┌──────────────────────────────────────────────────────────┐
│ After running with LITE for a while...                   │
│ "We're ready for production!"                            │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────↓─────────────────────────────────────┐
│ LITE-TO-FULL-MIGRATION.md                                │
│ - Decision matrix (when to upgrade)                      │
│ - 7 phases (30 min)                                      │
│ - What changes (10→15 princ, 5→16 rules, etc)            │
│ - Rollback plan                                          │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ↓
            ✅ UPGRADED TO FULL
            (production ready)
```

---

## 📊 Quick Reference: Who Goes Where?

| Role | Scenario | Start | Time |
|------|----------|-------|------|
| **Tech Lead** | Adding new project | INTEGRATION/README | 30 min total |
| **Tech Lead** | (part 1) Setup & config | INTEGRATION/STEP_1-5 | 20 min |
| **Tech Lead** | (part 2) Detect intention | INTEGRATION/STEP_6 | 10 min |
| **Developer** | First time setup | EXECUTION/_START_HERE | 15-40 min |
| **Developer** | Implementing feature | EXECUTION/_START_HERE | 1-8 hours |
| **Team** | Switching LITE→FULL | LITE-TO-FULL-MIGRATION | 30 min |
| **New User** | Just learning SDD | adoption/INDEX | 10 min |
| **AI Agent** | Autonomous execution | .ai-index | n/a |

---

## 🎯 Decision Points

### Point 1: "Where do I start?"

```
README.md has decision tree
  ↓
Choose: Integration? Execution? Learning? AI?
  ↓
→ Follow your path
```

### Point 2: "How does integration work?"

```
INTEGRATION/README.md explains 2 phases:
  ↓
Phase 1 (STEPS 1-5): Technical setup (same for everyone)
Phase 2 (STEP 6): Detect intention → LITE or FULL
  ↓
→ Answer questions to find your governance level
```

### Point 3: "LITE or FULL?" (After Integration)

```
INTEGRATION/STEP_6.md has 5 questions
  ↓
Answer honestly about:
- Team size
- Project type
- Compliance needs
- AI agent usage
- Error cost
  ↓
→ Score determines LITE or FULL
```

### Point 4: "What workflow do I follow?" (During Execution)

```
adoption/{LITE,FULL}-ADOPTION.md or AGENT_HARNESS.md
  ↓
Follow phases (3 for LITE, 7 for FULL)
  ↓
→ Implement with appropriate governance level
```

---

## ✅ Validation Checklist at Each Point

### After "Technical Setup Complete" (STEP 5)

- ✅ Project directories created
- ✅ Templates copied
- ✅ `.spec.config` points to SDD
- ✅ Validation script passed
- ✅ Changes committed
- ✅ Ready for STEP 6

### After "Intention Detected" (STEP 6)

- ✅ Answered 5 questions honestly
- ✅ Know if LITE or FULL
- ✅ `.spec.config` includes `adoption_level`
- ✅ Team aligned on choice
- ✅ Intention documented
- ✅ Ready for EXECUTION

### After "Setup Complete" (EXECUTION: PHASE_0)

- ✅ `.providence/` fully configured for your level
- ✅ Pre-commit hooks installed
- ✅ Documentation available (LITE or FULL)
- ✅ Developer can start implementing

### After "Feature Implemented"

- ✅ Code follows layers (10 for LITE, 8 for FULL)
- ✅ Tests passing (10 DoD for LITE, 45 for FULL)
- ✅ Decisions documented (light for LITE, complete ADR for FULL)
- ✅ PR ready for review

---

## 🚀 Time Estimates by Path

```
Total Project Setup (Integration + First Feature)

LITE Path:
  Integration:        30 min
  Setup (PHASE_0):    15 min
  Feature impl:       1-2 hours
  ─────────────────
  Total:              2-2.5 hours

FULL Path:
  Integration:        30 min
  Setup (PHASE_0):    40 min
  Feature impl:       1.5-3 hours
  ─────────────────
  Total:              2.5-4 hours

Migration (LITE→FULL):
  One-time:           30 min
  Future features:    +30% complexity
```

---

## 📚 File Directory Quick Ref

```
Root
├── README.md ..................... Main entry, shows LITE/FULL choice
├── .ai-index.md .................. AI agents
│
├── INTEGRATION/
│   ├── README.md ................. Project integration (mentions LITE/FULL)
│   ├── CHECKLIST.md .............. Step-by-step (STEP_0: choose adoption)
│   └── STEP_*.md ................. Individual steps
│
├── EXECUTION/
│   ├── _START_HERE.md ............ Feature impl (STEP_0: confirm adoption)
│   ├── NAVIGATION.md ............. Doc search
│   ├── spec/
│   │   ├── CANONICAL/ ............ Constitutional rules
│   │   ├── guides/
│   │   │   └── adoption/
│   │   │       ├── INDEX.md ..................... Decision tree
│   │   │       ├── LITE-ADOPTION.md ............ 15 min setup
│   │   │       ├── FULL-ADOPTION.md ............ 40 min setup
│   │   │       ├── LITE-TO-FULL-MIGRATION.md .. 30 min upgrade
│   │   │       ├── MULTI-LANGUAGE-EXPLORATION.md  v3.0 roadmap
│   │   │       └── ONBOARDING-FLOW.md ......... This file
│   │   └── ...
│   └── ...
│
└── context/
    └── runtime-state/
        └── analysis/ ............. Historical docs
```

---

## 🎯 Next Actions Based on Your Scenario

### "I'm totally new to SDD"

1. Read: [README.md](../../../README.md) (5 min)
2. Choose: [adoption/INDEX.md](./INDEX.md) (5 min)
3. Read: [adoption/LITE-ADOPTION.md](./LITE-ADOPTION.md) or [FULL-ADOPTION.md](./FULL-ADOPTION.md) (15-40 min)

### "I'm adding a new project"

1. Read: [INTEGRATION/CHECKLIST.md](../integration/CHECKLIST.md) (5 min)
2. Follow: [INTEGRATION/CHECKLIST.md](../integration/CHECKLIST.md) STEP 1-5 (20 min, technical)
3. Follow: [INTEGRATION/STEP_6.md](../integration/STEP_6.md) (10 min, detect intention)
4. Choose: LITE or FULL based on answers

### "I'm implementing now"

1. Confirm: Your adoption level (check `.spec.config` adoption_level)
2. Read: [CORE__START_HERE.md](../operational/CORE__START_HERE.md) (5 min)
3. Follow: AGENT_HARNESS phases (1-8 hours)

### "I have questions"

1. Search: [NAVIGATION.md](../operational/NAVIGATION.md)
2. Read: [FAQ.md](../faq.md)
3. Ask: Create an issue or discussion

---

**Framework under active development.**
**Your feedback shapes the roadmap!**

*Last updated: April 19, 2026*
