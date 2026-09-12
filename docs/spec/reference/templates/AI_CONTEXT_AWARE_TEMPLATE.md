# 🧠 Context-Aware Template — Follow This Structure

> **Purpose:** Template for standardized .providence/context-aware/ setup in new projects
> **Standard:** Framework Standards v1.0 (3-tier structure)
> **Location:** Use this to bootstrap new project's context structure

---

## 📋 What This Is

When you create a new project with SDD INTEGRATION, copy this template to:

```
your-project/.providence/context-aware/
```

---

## 🗂️ Complete Directory Structure

```
.providence/context-aware/
├── README.md                              ← Main navigation hub
├── QUICK_STATUS.md                        ← Sprint snapshot
│
├── summaries/                             ← Compact summaries
│   ├── RECENT_TASKS.md
│   └── OPEN_ISSUES.md
│
├── task-progress/                         ← Active work
│   ├── _current.md                       ← Edit this daily
│   └── completed/                        ← Archive folder
│
├── analysis/                              ← Findings
│   ├── _current-issues.md                ← Known problems
│   └── [project-specific]/               ← Project findings
│
└── runtime-state/                         ← System health
    └── _current.md                       ← Metrics, status
```

---

## 📝 Files to Create

### 1. README.md (Navigation Hub)

```markdown
# 🧠 Context-Aware — [PROJECT_NAME]

**Purpose:** Store agent-created context during development
**Updated:** [YYYY-MM-DD]
**Structure:** 3-tier (QUICK_STATUS + summaries + task-progress)

## 🗂️ Directory Structure
[Copy structure from above]

## 🎯 Quick Navigation
[Update with project-specific links]

## 🤖 For Agents
[Copy agent workflow section]

## 📈 Token Efficiency
[Standard section - applies to all projects]
```

### 2. QUICK_STATUS.md (Sprint Snapshot)

```markdown
# ⚡ Quick Status — [PROJECT_NAME]

## 📊 Sprint Status
[Create table with current initiatives]

## 🎯 Current Focus
[List active work areas]

## 📈 Key Metrics
[Add project metrics]

## 🔗 Quick Links
[Update with project-specific links]
```

### 3. summaries/RECENT_TASKS.md (Completed Work)

```markdown
# 📝 Recent Tasks

## ✅ Recently Completed
[Document completed items]

## 📋 In Progress
[Current work items]

## 📚 Archive
Previous work in: task-progress/completed/
```

### 4. summaries/OPEN_ISSUES.md (Blockers)

```markdown
# ⚠️ Open Issues & Blockers

## Status
[Green/Yellow/Red assessment]

## Known Issues
[List current blockers]

## Next Steps
[Recommended actions]
```

### 5. task-progress/_current.md (Active Tasks)

```markdown
# Task Progress — [PROJECT_NAME]

**Last Updated:** [Date]
**Updated By:** [Agent Name]

## 🔄 Active Tasks

### Task 1: [Name]
- **Status:** In Progress 🔵
- **Started:** [Date]
- **Subtasks:**
  - [ ] Subtask 1
  - [ ] Subtask 2

[Add more tasks as needed]
```

### 6. analysis/_current-issues.md (Known Problems)

```markdown
# Current Issues — [PROJECT_NAME]

**Last Updated:** [Date]

## Known Problems

- Issue 1: [Description]
- Issue 2: [Description]

## Workarounds

[Document any temporary solutions]

## For Next Agent

[Key context for continuity]
```

### 7. runtime-state/_current.md (System Status)

```markdown
# Runtime State — [PROJECT_NAME]

**Last Updated:** [Date]

## System Health
- Health: 🟢 [Status]
- Last deployment: [Date]
- Current issues: [Count]

## Metrics
[Project-specific metrics]

## Active Threads
[Any concurrent work]
```

---

## ✅ Setup Checklist

For new projects:

- [ ] Copy this template to `.providence/context-aware/`
- [ ] Edit README.md with project-specific info
- [ ] Update QUICK_STATUS.md with initial state
- [ ] Create initial entries in summaries/
- [ ] Initialize task-progress/_current.md
- [ ] Create analysis/_current-issues.md with known issues
- [ ] Set up runtime-state/_current.md
- [ ] Commit with message: "feat: initialize context-aware structure per framework standards"

---

## 🔄 Weekly Maintenance

1. **Update QUICK_STATUS.md** with current sprint info
2. **Move completed tasks** from task-progress/_current.md to summaries/RECENT_TASKS.md
3. **Clean up** OPEN_ISSUES.md
4. **Archive** old entries

---

## 💡 Token Budget

Typical agent session:

- QUICK_STATUS: ~300 tokens (2 min read)
- summaries/ (2 files): ~500 tokens (5 min read)
- task-progress: ~400 tokens (5 min read)

**Total:** ~1,200 tokens per session (vs 5,600+ with monolithic approach)

---

## 🔗 Reference

**Full Standards:** [Context Management Standards](./CONTEXT_MANAGEMENT_STANDARDS.md)
**Framework:** SDD v3.0
**Created:** April 19, 2026

---

## ⚠️ Important Notes

- Keep QUICK_STATUS.md current (updated weekly minimum)
- Archive completed tasks regularly to keep _current.md manageable
- Use consistent naming (QUICK_STATUS, RECENT_TASKS, OPEN_ISSUES)
- Link between files for navigation
- Don't let any file exceed 1,000 lines

---

**Template Version:** 1.0
**Status:** Production
**Last Updated:** April 19, 2026
