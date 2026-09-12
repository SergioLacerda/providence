# 🤖 .ai/ Infrastructure Guide

**This directory contains AI agent runtime state and context for SDD governance**

---

## 📁 Directory Structure

```
.ai/
├── README.md (this file)
├── context-aware/
│   ├── task-progress/      (track current work)
│   ├── analysis/           (document decisions)
│   └── runtime-state/      (execution state)
└── runtime/
    ├── search-keywords.md  (find docs quickly)
    ├── spec-canonical-index.md
    └── spec-guides-index.md
```

---

## 🎯 Purpose of Each Subdirectory

### .ai/context-aware/

**Task Progress:** Track what you're working on
- File: `task-progress/_current.md`
- When: Update after each phase
- What: Current task, phase, blockers

**Analysis:** Document decisions and discoveries
- File: `analysis/_current.md`
- When: Update during PHASE 5-6
- What: Decisions, risks, learnings

**Runtime State:** Track who's working on what
- File: `runtime-state/execution-state.md`
- When: Check before starting (PHASE 2)
- What: Current threads, owners, status

### .ai/runtime/

**Search Keywords:** Find documentation quickly
- File: `search-keywords.md`
- When: Use during PHASE 4 (load context)
- What: Keyword → file location mapping

**CANONICAL Index:** Quick reference to immutable authority
- File: `spec-canonical-index.md`
- When: When you need to understand core rules
- What: Constitution, rules, decisions, specifications

**Guides Index:** Quick reference to operational guides
- File: `spec-guides-index.md`
- When: When you need help on specific topics
- What: Onboarding, operational, emergency guides

---

## 🚀 How to Use

### Before You Start (PHASE 2)
```bash
cat .ai/context-aware/runtime-state/execution-state.md
# Check: Is anyone working on your task?
```

### Loading Context (PHASE 4)
```bash
cat .ai/runtime/search-keywords.md
# Search for topics you need to understand
# Each entry points to framework docs
```

### During Implementation (PHASE 5)
```bash
echo "Current task: [description]" >> .ai/context-aware/task-progress/_current.md
# Update progress file as you work
```

### Before PR (PHASE 6)
```bash
cat .ai/context-aware/analysis/_current.md
# Add decisions, risks, learnings
```

---

## 📋 Setup Checklist

After integration, verify:

- [ ] `.ai/context-aware/` exists
- [ ] `.ai/context-aware/task-progress/` has files
- [ ] `.ai/context-aware/analysis/` has files
- [ ] `.ai/context-aware/runtime-state/` has execution-state.md
- [ ] `.ai/runtime/search-keywords.md` has 100+ lines
- [ ] `.ai/runtime/spec-canonical-index.md` exists
- [ ] `.ai/runtime/spec-guides-index.md` exists

If any are missing, run PHASE 0 setup script:
```bash
python $(grep spec_path ../.spec.config | cut -d' ' -f3)/docs/ia/SCRIPTS/phase-0-agent-onboarding.py
```

---

## 🔗 Learn More

**Full framework:** Read `.spec.config` for path, then:
- Entry: `{path}/EXECUTION/_START_HERE.md`
- Guides: `{path}/EXECUTION/spec/guides/`
- Rules: `{path}/EXECUTION/spec/CANONICAL/rules/`

---

## ⚡ Quick Commands

```bash
# Check execution state (before starting)
cat .ai/context-aware/runtime-state/execution-state.md

# Search for documentation
grep "topic" .ai/runtime/search-keywords.md

# Track your progress
echo "PHASE 5: Implementing feature X" >> .ai/context-aware/task-progress/_current.md

# Find rules
grep -r "Rule" .ai/runtime/spec-canonical-index.md
```

---

**Need help?** Framework: `{spec_path}/EXECUTION/spec/guides/reference/FAQ.md`
