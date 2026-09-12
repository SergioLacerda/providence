# 📚 EXECUTION — AGENT_HARNESS Development Workflow

**For:** Developers/agents developing features on projects using SDD framework
**Duration:** 40 minutes (PHASE 0) + ongoing work
**Complexity:** 7 clear phases, each with own entry point
**Outcome:** Feature implemented, tests passing, checkpoint documented

---

## 🎯 What is Execution?

Execution = using SDD framework to implement work (features, bugs, improvements).

The workflow is **AGENT_HARNESS: 7 Phases**

1. **PHASE 1:** Lock to Rules (read constitution, pass quiz)
2. **PHASE 2:** Check Execution State (detect conflicts)
3. **PHASE 3:** Choose PATH (A=bug, B=simple feature, C=complex, D=multithread)
4. **PHASE 4:** Load Context (from SDD, on-demand)
5. **PHASE 5:** Implement (with TDD, track in .providence/)
6. **PHASE 6:** Validate (tests pass, definition of done)
7. **PHASE 7:** Checkpoint (update state, create PR)

---

## 🚀 Execution Workflow

```
Start: You have a task to implement
  ↓
[PHASE 1] Read: constitution.md + ia-rules.md
          Pass: VALIDATION_QUIZ (≥80%)
  ↓
[PHASE 2] Check: .providence/context-aware/ for conflicts
  ↓
[PHASE 3] Choose: PATH A/B/C/D (load right docs)
  ↓
[PHASE 4] Search: .providence/runtime/search-keywords.md
          Load: docs you need (on-demand)
  ↓
[PHASE 5] Implement: Feature + tests (TDD)
          Track: in .providence/context-aware/task-progress/
  ↓
[PHASE 6] Run: Tests, check definition_of_done
          Update: .providence/context-aware/analysis/
  ↓
[PHASE 7] Checkpoint: Document decisions + risks
          Create: PR with checkpoint info
  ↓
End: Feature complete, ready for review
```

---

## 📍 Start Here

**New to SDD?** → [_START_HERE.md](./_START_HERE.md)

**Know what you need?** → [NAVIGATION.md](./NAVIGATION.md) (search by task)

**Want specific phase info?** → See INDEX below

---

## 📚 Full Index

| Phase | Document | Duration | When |
|-------|----------|----------|------|
| **Intro** | [_START_HERE.md](./_START_HERE.md) | 5 min | First time |
| **Search** | [NAVIGATION.md](./NAVIGATION.md) | 2 min | Finding specific doc |
| **Phase 1** | spec/CANONICAL/rules/ | 15 min | First thing |
| **Phase 2** | spec/custom/[YOUR_PROJECT]/ | 5 min | Check state |
| **Phase 3** | spec/guides/AGENT_HARNESS.md | 5 min | Choose path |
| **Phase 4** | spec/runtime/search-keywords.md | 5 min | Load context |
| **Phase 5** | spec/CANONICAL/specifications/ | 20 min | Implement |
| **Phase 6** | spec/CANONICAL/specifications/definition-of-done.md | 10 min | Validate |
| **Phase 7** | spec/custom/[YOUR_PROJECT]/execution-state/ | 5 min | Checkpoint |

---

## 🔗 Key Resources

**Mandatory Reading:**
- [spec/CANONICAL/rules/constitution.md](./spec/CANONICAL/rules/constitution.md) — 15 immutable principles
- [spec/CANONICAL/rules/ia-rules.md](./spec/CANONICAL/rules/ia-rules.md) — 16 mandatory rules
- [spec/guides/onboarding/AGENT_HARNESS.md](./spec/guides/onboarding/AGENT_HARNESS.md) — 7-phase workflow

**Emergency Help:**
- [spec/guides/emergency/README.md](./spec/guides/emergency/) — 5 crisis procedures
- [spec/guides/operational/README.md](./spec/guides/operational/) — 7 operational guides

**Reference:**
- [spec/guides/reference/FAQ.md](./spec/guides/reference/FAQ.md) — Common questions
- [spec/guides/reference/GLOSSARY.md](./spec/guides/reference/GLOSSARY.md) — Terminology

---

## ✅ Success Criteria

After completing all 7 phases:

- ✅ Feature implemented (code written)
- ✅ Tests passing (100% coverage for new code)
- ✅ Definition of done checked (45+ items)
- ✅ .providence/context-aware/task-progress/ updated
- ✅ .providence/context-aware/analysis/ captures learnings
- ✅ Checkpoint created (decisions + risks documented)
- ✅ PR ready for review

---

## 🎯 Next Steps

**First time?** → [_START_HERE.md](./_START_HERE.md)

**Looking for specific help?** → [NAVIGATION.md](./NAVIGATION.md)

**Ready to implement?** → [guides/onboarding/AGENT_HARNESS.md](../../../../../docs/spec/guides/onboarding/AGENT_HARNESS.md)

---

**Status:** Ready to develop
**Support:** See emergency/ guides if stuck
