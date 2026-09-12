# 🧠 Context-Aware Dynamics — Project-Specific AI Memory

**Location:** `.ai/context-aware/`  
**Purpose:** Store dynamic, project-specific context that agents create  
**Ownership:** Development team + AI agents  
**Created:** During PHASE 0 agent onboarding  

---

## 📋 What Goes Here?

This folder is created by agents during workspace initialization (PHASE 0).

It stores **dynamic context** that changes as agents work:

```
.ai/context-aware/
├── task-progress/           ← Current task status
│   ├── _current.md         ← Active tasks NOW
│   └── completed/          ← Finished tasks (archive)
│
├── analysis/               ← Discoveries agents make
│   ├── _current-issues.md  ← Known problems (living list)
│   └── [specific findings] ← Project-specific analysis
│
└── runtime-state/          ← Live system status
    └── _current.md         ← Health, metrics, threads
```

---

## 🤖 For Agents: Quick Start

### When Starting Work

```bash
# 1. Check current tasks
cat .ai/context-aware/task-progress/_current.md

# 2. Review known issues
cat .ai/context-aware/analysis/_current-issues.md

# 3. Check system status
cat .ai/context-aware/runtime-state/_current.md

# 4. Begin work
```

### When Finishing Work

```bash
# 1. Update task progress
vi .ai/context-aware/task-progress/_current.md

# 2. Document any findings
vi .ai/context-aware/analysis/_current-issues.md

# 3. Commit your context
git add .ai/context-aware/
git commit -m "📝 Update context: [what changed]"
```

---

## 📚 Full Documentation

See: `docs/ia/guides/runtime/CONTEXT_AWARE_USAGE.md` (in SPEC framework)

For complete guide on:
- How to structure task-progress
- How to document analysis
- How to track runtime-state
- Workflow examples
- Common mistakes

---

## ✅ Next Steps

1. **Read:** `docs/ia/guides/runtime/CONTEXT_AWARE_USAGE.md`
2. **Create:** Your first task entry in task-progress/_current.md
3. **Track:** As you work, update context files
4. **Share:** Commit to git so next agent sees it

---

**This folder is created by PHASE 0. You're not starting from scratch!** 🚀
