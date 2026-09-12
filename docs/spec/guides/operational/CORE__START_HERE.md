# 🚀 START HERE — EXECUTION Workflow

**You're about to implement something. This guide gets you oriented.**

---

## 🎯 STEP 0: Choose Your Adoption Path (Mandatory First)

**Have you picked LITE or FULL?**

### If NO → Do this NOW (5 min)

Go to: **[adoption/INDEX.md](../adoption/INDEX.md)**

- Read the comparison table
- Choose LITE (15 min, learning) or FULL (40 min, production)
- Come back here once decided

### If YES → Continue below ✅

Your choice affects:

- ✅ Which principles you follow (10 vs 15)
- ✅ Which rules you enforce (5 vs 16)
- ✅ Setup time (15 vs 40 min)
- ✅ Which workflows you use (3 vs 7 phases)

**Can't remember which you chose?** Check `.spec.config` or ask in your team channel.

---

## ❓ What Are You Doing?

Pick ONE:

### 1️⃣ **"This is my first time using SDD"**

You need to set up your development environment with SDD governance.

→ **First:** Confirm you chose LITE or FULL (see STEP 0 above)

→ **Then read:** [PHASE_0_SETUP.md](.docs/spec/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md)

→ **Your setup will use:**

- LITE: 5 essential rules + 10 DoD
- FULL: 16 mandatory rules + 45 DoD

*Output: `.providence/` infrastructure created with your adoption level, you're ready to work*

**Time:** 15 min (LITE) or 40 min (FULL) + PHASE_0

---First:** Confirm you chose LITE or FULL (see STEP 0 above)

→ **Then read:** [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md)

→ **Then:** Choose your PATH (A=bug, B=simple feature, C=complex, D=multithread)

→ **Your workflow will have:**

- LITE: Simplified checklist (easier, faster)
- FULL: Complete checklist (thorough, auditable

You have a task assigned. You want to implement it following SDD rules.

→ **Read:** [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md)

→ **Then:** Choose your PATH (A=bug, B=simple feature, C=complex, D=multithread)

*Output: Feature implemented, tests passing, checkpoint documented*

**Time:** Depends on complexity (30 min → 2 days)

---

### 3️⃣ **"Something broke, I need help now"**

Production emergency? Test failure? Governance violation?

→ **Read:** [Emergency Procedures](.docs/spec/guides/emergency/README.md)

Pick from:

- `PRE_COMMIT_HOOK_FAILURE.md` — Hook is blocking commits
- `TEST_FAILURE_GUIDE.md` — Tests failing unexpectedly
- `RULES_VIOLATION_DETECTED.md` — CI blocked for rule violation
- `IMPORTS_CORRUPTED.md` — Import system broken
- `METRICS_CORRUPTION.md` — Metrics don't make sense

*Output: Issue resolved, root cause documented*

**Time:** 10-30 minutes

---

### 4️⃣ **"I need to find specific documentation"**

You don't have a task—you just want to read about something.

→ **Read:** [NAVIGATION.md](./NAVIGATION.md)

*Use keyword search to find docs*

**Time:** 2-5 minutes

---

### 5️⃣ **"I have questions about how SDD works"**

Confused about architecture? Rules? Workflow?

→ **Read:** [FAQ.md](.docs/spec/guides/reference/FAQ.md) or [GLOSSARY.md](.docs/spec/guides/reference/GLOSSARY.md)

*Output: Clarification + links to detailed docs*

**Time:** 5-15 minutes

---

## 📋 LITE vs FULL — Key Differences

| Aspect | LITE | FULL |
|--------|------|------|
| **Setup** | 15 min | 40 min |
| **Principles** | 10 core | 15 complete |
| **Rules** | 5 essential | 16 mandatory |
| **DoD** | 10 criteria | 45 criteria |
| **Phases** | 3 simplified | 7 full workflow |
| **Best for** | Learning, <5 people | Production, mission-critical |
| **Upgrade** | → FULL (30 min) | — |

---

## 🎯 Workflow Phases (Your adoption level affects detail)

If you picked **#2 above**, here's what you'll do:

```
PHASE 1: Lock to Rules (10-15 min)
  LITE:  → Read 10 principles
  FULL:  → Read 15 principles + ia-rules
  → Pass VALIDATION_QUIZ (≥80%)

PHASE 2: Check Execution State (5 min)
  → Look at .providence/context-aware/
  → Make sure no one else is working on this

PHASE 3: Choose PATH (5 min)
  → A = Bug fix
  → B = Simple feature (1-2 days)
  → C = Complex feature (3+ days)
  → D = Multi-thread work (coordinated)

PHASE 4: Load Context (5-20 min)
  LITE:  → Read simplified docs for your PATH
  FULL:  → Search .providence/runtime/search-keywords.md
  → Read only docs for your PATH

PHASE 5: Implement (1-8 hours)
  → Write code + tests (TDD)
  → Track progress in .providence/context-aware/task-progress/

PHASE 6: Validate (5-15 min)
  → All tests pass
  LITE:  → Check definition_of_done (10 items)
  FULL:  → Check definition_of_done (45+ items)

PHASE 7: Checkpoint (5-10 min)
  → Document decisions
  LITE:  → Light documentation
  FULL:  → Complete ADR + risks
```

**Total setup time:** 15-40 min (one time, depends on LITE vs FULL)
**Implementation time:** Depends on complexity + adoption level

---

## ✅ Quick Validation

Before continuing, confirm:

- ✅ You have `.spec.config` in project root
- ✅ It points to providence (check: `cat .spec.config`)
- ✅ You have `.providence/runtime/` directory
- ✅ PHASE 0 has been run (creates `.providence/` infrastructure)

If something is missing → [PHASE_0_SETUP.md](.docs/spec/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md)

---

## 🔗 Key Entry Points

| Scenario | Read This |
|----------|-----------|
| First time setup | [PHASE-0-AGENT-ONBOARDING.md](.docs/spec/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md) |
| Implementing feature | [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md) |
| Emergency/blocked | [Emergency Procedures](.docs/spec/guides/emergency/README.md) |
| Need to find docs | [NAVIGATION.md](./NAVIGATION.md) |
| Questions | [FAQ.md](.docs/spec/guides/reference/FAQ.md) |

---

## 🚀 Next Action

Pick your scenario from the 5 above, then follow the link.

**Uncertain?** Start with [NAVIGATION.md](./NAVIGATION.md) — you'll find what you need.

---

**This page:** 5-minute orientation
**Status:** Ready
**Last updated:** April 19, 2026
