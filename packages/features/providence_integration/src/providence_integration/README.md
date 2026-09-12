# 🔗 INTEGRATION — Add Your Project to SDD Framework

**For:** Teams integrating a new (or existing) project with SDD governance
**Duration:** 30 minutes total (20 min technical setup + 10 min intention detection)
**Complexity:** Simple (no decisions during setup, but questions at the end)
**Outcome:** Project ready for development with appropriate governance level (LITE or FULL)

---

## 📍 Navigation

**Want to integrate now?** → [CHECKLIST.md](./CHECKLIST.md)
**Want to understand first?** → [guides/INDEX.md](./guides/INDEX.md) — Concepts & comparisons

---

## 🎯 How Integration Works

**Phase 1: Technical Setup (STEPS 1-5)** — Same for everyone
- Copy templates
- Configure `.spec.config`
- Validate installation
- No decisions needed here

**Phase 2: Intention Detection (STEP 6)** — Find your governance level
- Answer questions about your project
- Responses determine LITE vs FULL
- Update `.spec.config` with adoption level

**Phase 3: Execute** — Use LITE or FULL as needed
- Developers follow AGENT_HARNESS with your level
- Can upgrade LITE→FULL anytime (30 min migration)

---

## 🚀 6-Step Process

| Step | What | Time | For |
|------|------|------|-----|
| **1** | Setup project structure | 5 min | Everyone |
| **2** | Copy templates | 5 min | Everyone |
| **3** | Edit `.spec.config` | 2 min | Everyone |
| **4** | Run validation script | 5 min | Everyone |
| **5** | Git commit | 3 min | Everyone |
| **6** | Detect intention (LITE or FULL) | 10 min | Project lead |

**Total:** 20 min (technical) + 10 min (intention) = 30 min guaranteed

---

## 📋 Before You Start

Make sure you have:
- ✅ Your project repository (git init already done)
- ✅ Access to this providence repo
- ✅ Python 3.8+ installed (for validation script)
- ✅ 30 minutes uninterrupted time
- ℹ️ **Note:** You'll answer questions AFTER technical setup (Step 6)

---

## ✅ Success Criteria

After completing all 6 steps, your project should have:

```
your-project/
├── .spec.config                    ← Points to ../providence + adoption_level
├── .github/copilot-instructions.md ← From templates/
├── .vscode/ai-rules.md             ← From templates/ (filtered for your level)
├── .cursor/rules/spec.mdc          ← From templates/
└── .providence/
    ├── context-aware/
    │   ├── task-progress/
    │   ├── analysis/
    │   └── runtime-state/
    └── runtime/
        ├── README.md
        ├── search-keywords.md
        ├── spec-canonical-index.md
        └── spec-guides-index.md (filtered for your adoption level)
```

And:
- ✅ `.spec.config` correctly points to providence
- ✅ `.spec.config` includes `adoption_level` (lite or full)
- ✅ Validation script ran successfully
- ✅ Team understands your adoption level
- ✅ Ready to start EXECUTION with AGENT_HARNESS

---

## 📍 Next: Follow the Checklist

[→ INTEGRATION/CHECKLIST.md](./CHECKLIST.md) — Step-by-step with commands

Or go directly to a specific step:
- [STEP_1.md](./STEP_1.md) — Setup directories
- [STEP_2.md](./STEP_2.md) — Copy templates
- [STEP_3.md](./STEP_3.md) — Configure `.spec.config`
- [STEP_4.md](./STEP_4.md) — Validate
- [STEP_5.md](./STEP_5.md) — Commit
- [STEP_6.md](./STEP_6.md) — Detect Intention (new!)

---

## 🎓 Understanding Integration (Guides)

Want to understand the concepts first?

- **[How does integration work?](./guides/INDEX.md)** → Overview + guides
- **[V1 vs V2 evolution](./guides/INTENTION-DETECTION-CONCEPT.md)** → Why intention-driven
- **[Compare adoption paths](./guides/V1-vs-V2-COMPARISON.md)** → LITE vs FULL

---

**Status:** Ready to integrate
**Support:** See STEP_X_* files for troubleshooting or [guides/INDEX.md](./guides/INDEX.md) for concepts
├── .github/copilot-instructions.md ← From templates/
├── .vscode/ai-rules.md             ← From templates/ (LITE or FULL version)
├── .cursor/rules/spec.mdc          ← From templates/
└── .providence/
    ├── context-aware/
    │   ├── task-progress/
    │   ├── analysis/
    │   └── runtime-state/
    └── runtime/
        ├── README.md
        ├── search-keywords.md
        ├── spec-canonical-index.md
        └── spec-guides-index.md (LITE or FULL filtered)
```

And:
- ✅ `.spec.config` correctly points to providence AND adoption level
- ✅ Validation script ran successfully
- ✅ Git shows new files ready to commit
- ✅ Developer can read docs in `.providence/runtime/` filtered for their adoption level

---

## 📍 Next: Follow the Checklist

[→ INTEGRATION/CHECKLIST.md](./CHECKLIST.md) — Step-by-step with commands

Or go directly to a specific step:
- [STEP_0.md](./STEP_0.md) ← Choose adoption level
- [STEP_1.md](./STEP_1.md)
- [STEP_2.md](./STEP_2.md)
- [STEP_3.md](./STEP_3.md)
- [STEP_4.md](./STEP_4.md)
- [STEP_5.md](./STEP_5.md)

---

**Status:** Ready to integrate
**Support:** See STEP_X_* files for troubleshooting
