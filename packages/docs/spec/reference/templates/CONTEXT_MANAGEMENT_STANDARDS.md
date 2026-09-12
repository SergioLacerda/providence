# 📋 Context Management Standards

> **Authority:** Framework-wide standardization for AI agent context operations
> **Version:** 1.0 | **Status:** Production
> **Applies to:** All `context/` and `.providence/context-aware/` directories across projects

---

## 🎯 Purpose

Standardize how projects manage context to ensure:

- ✅ Consistent structure across all projects
- ✅ Token efficiency (agents read only what they need)
- ✅ Scalability (works from small to enterprise)
- ✅ Maintainability (clear conventions)
- ✅ Discoverability (agents find what they need)

---

## 📊 The 3-Tier Context Structure

All context directories MUST follow this pattern:

```
{context-dir}/
├── README.md                    ← Navigation hub + purpose
├── QUICK_REFERENCE.md           ← 50-75 lines, ~300-400 tokens
├── summaries/                   ← Compact docs (40-60 lines each)
│   ├── SUMMARY_1.md
│   ├── SUMMARY_2.md
│   └── [topic]_SUMMARY.md
└── detailed/                    ← Full documentation (100+ lines)
    ├── DETAIL_1_FULL.md
    ├── DETAIL_2_FULL.md
    └── [topic]_FULL.md
```

### Tier 1: QUICK_REFERENCE.md (~300 tokens)

**Purpose:** Answer "What's the status NOW?"
**Length:** 50-75 lines
**Content:**

- Status matrix (table format)
- Essential links (organized by role/use case)
- Key metrics summary

**Agent Use:** Read first for quick answers

---

### Tier 2: summaries/ (40-60 lines each, ~250 tokens)

**Purpose:** Provide summary for specific topic/phase
**Length:** 40-60 lines
**Content:**

- Topic headline
- Key accomplishments (3-5 bullets)
- Status metrics (compact table)
- Link to full details

**Agent Use:** Read when asking about specific topic

---

### Tier 3: detailed/ (~700 tokens)

**Purpose:** Complete reference documentation
**Length:** 100+ lines
**Content:**

- Full narrative
- Complete metrics
- All decisions documented
- Historical context

**Agent Use:** Read only for deep understanding

---

## 🚀 Token Efficiency Gains

**Before (monolithic single README):**

```
Single 400-500 line file = 5,600-7,000 tokens
Every query requires reading entire document
```

**After (3-tier structure):**

```
QUICK_REFERENCE:    ~300 tokens (status checks)
summaries/topic:    ~250 tokens (specific questions)
detailed/topic:     ~700 tokens (deep dives)

Typical agent query: 300-700 tokens (vs 5,600)
SAVINGS: 66-87% token reduction
```

---

## 📦 Two Context Types

### TYPE A: Documentation Context

**Examples:** `/context/` (framework phases), project documentation
**Use 3-tier structure for:** PHASES, GUIDES, ARCHITECTURE
**Update cadence:** Infrequent (per phase/milestone)

**Template:**

```
doc-context/
├── README.md
├── QUICK_REFERENCE.md
├── summaries/
│   ├── PHASE_1_SUMMARY.md
│   ├── PHASE_2_SUMMARY.md
│   └── ...
└── detailed/
    ├── PHASE_1_FULL.md
    ├── PHASE_2_FULL.md
    └── ...
```

---

### TYPE B: Runtime Context

**Examples:** `.providence/context-aware/` (agent work tracking)
**Use 3-tier structure for:** TASK-PROGRESS, ANALYSIS, METRICS
**Update cadence:** Frequent (per task/session)

**Template:**

```
.providence/context-aware/
├── README.md
├── QUICK_STATUS.md          ← Current sprint status
├── summaries/
│   ├── RECENT_TASKS.md      ← Last 5-10 completed
│   └── OPEN_ISSUES.md       ← Known blockers
├── task-progress/
│   ├── _current.md          ← Active tasks NOW
│   └── completed/           ← Archive
├── analysis/
│   ├── _current-issues.md   ← Known problems
│   └── [findings]/
└── runtime-state/
    └── _current.md          ← System health
```

---

## ✅ Implementation Checklist

### For New Documentation Context

- [ ] Create `/context/` or equivalent in project
- [ ] Create `README.md` with navigation hub
- [ ] Create `QUICK_REFERENCE.md` (status matrix + links)
- [ ] Create `summaries/` folder
- [ ] Create `detailed/` folder
- [ ] Move full docs → `detailed/`
- [ ] Create compact summaries → `summaries/`
- [ ] Verify links all work
- [ ] Git commit with message: "refactor: apply context management standards - 3-tier structure for token efficiency"

### For Existing Runtime Context

- [ ] Create/update `QUICK_STATUS.md`
- [ ] Create `summaries/` folder if doesn't exist
- [ ] Create `RECENT_TASKS.md` (last completed work)
- [ ] Create `OPEN_ISSUES.md` (blockers/problems)
- [ ] Ensure `task-progress/`, `analysis/`, `runtime-state/` exist
- [ ] Git commit with message: "refactor: standardize context-aware structure per framework standards"

---

## 🎯 File Naming Conventions

**QUICK_REFERENCE.md:**

```
Always named: QUICK_REFERENCE.md (or QUICK_STATUS.md for runtime)
Never: Quick_Ref.md, STATUS.md, summary.md
```

**Summaries:**

```
Format: {TOPIC}_SUMMARY.md
Examples: PHASE_1_SUMMARY.md, RECENT_TASKS.md, OPEN_ISSUES.md
Length: 40-60 lines
Token budget: ~250 per file
```

**Detailed:**

```
Format: {TOPIC}_FULL.md
Examples: PHASE_1_FULL.md, ARCHITECTURE_FULL.md
Length: 100+ lines
Token budget: ~700 per file
```

---

## 📐 Directory Structure Rules

**Immutable:**

- README.md (top level, always)
- QUICK_REFERENCE.md or QUICK_STATUS.md (top level, always)

**Required:**

- summaries/ (folder, must exist)
- detailed/ (folder, must exist)

**Optional (context-specific):**

- task-progress/, analysis/, runtime-state/ (for .providence/context-aware/ only)
- Other topic-specific folders per project needs

---

## 🔗 Cross-References

In README.md, always include a table like:

```markdown
| Need | Look Here | Tokens | Time |
|------|-----------|--------|------|
| Quick status | QUICK_REFERENCE.md | ~300 | 2 min |
| Phase details | summaries/PHASE_X_SUMMARY.md | ~250 | 5 min |
| Full history | detailed/PHASE_X_FULL.md | ~700 | 15 min |
```

In summaries, always end with:

```markdown
**See full details:** [Template Source](./CONTEXT_MANAGEMENT_STANDARDS.md)
```

---

## 💾 Git Commit Pattern

### For Documentation Context

```bash
git add context/
git commit -m "refactor: apply context management standards - 3-tier structure

Add tiered documentation structure for token efficiency:
- QUICK_REFERENCE.md: ~300 tokens (status matrix)
- summaries/: ~250 tokens each (topic summaries)
- detailed/: ~700 tokens each (full documentation)

Result: 66-87% token reduction vs single-file approach"
```

### For Runtime Context

```bash
git add .providence/context-aware/
git commit -m "refactor: standardize context-aware per framework standards

Apply 3-tier structure:
- QUICK_STATUS.md: Sprint status, current metrics
- summaries/: Recent tasks, open issues
- task-progress/: Active tasks (unchanged)
- analysis/: Findings (unchanged)
- runtime-state/: System status (unchanged)

Improves discoverability and reduces context-read time for agents"
```

---

## 🧠 For Agents: How to Use

### When Context Exists

```bash
# 1. Start by reading quick reference
cat context/QUICK_REFERENCE.md         # ~300 tokens, 2 min

# 2. If you need topic details
cat context/summaries/TOPIC_SUMMARY.md # ~250 tokens, 5 min

# 3. If you need complete history
cat context/detailed/TOPIC_FULL.md     # ~700 tokens, 15 min
```

### When Creating/Updating Context

**For documentation:**

```
1. Create QUICK_REFERENCE.md first (status matrix)
2. Create summaries/ (compact per-topic)
3. Keep detailed/ (full reference)
```

**For runtime:**

```
1. Keep task-progress/_current.md (active work)
2. Update QUICK_STATUS.md weekly (sprint snapshot)
3. Move completed tasks to RECENT_TASKS.md
4. Update OPEN_ISSUES.md as needed
```

---

## 📝 Template: README Structure

All context README.md must include:

```markdown
# 📋 Context Directory — [Purpose]

> **Purpose:** [What is this context for?]
> **Token Efficiency:** [e.g., 66% reduction vs 5,600 tokens]
> **Last Updated:** [Date]

---

## 🗂️ Directory Structure

[Show the 3-tier structure]

---

## 🎯 Quick Navigation

| Need | Location | Tokens | Time |
|------|----------|--------|------|
| Quick status | QUICK_REFERENCE.md | ~300 | 2 min |
| [Topic 1] | summaries/TOPIC_1_SUMMARY.md | ~250 | 5 min |
| [Topic 2] | summaries/TOPIC_2_SUMMARY.md | ~250 | 5 min |
| Full [Topic 1] | detailed/TOPIC_1_FULL.md | ~700 | 15 min |

---

## 📖 Documentation

[Links to key docs]

---

**Context Management:** Following Framework Standards v1.0
```

---

## ⚠️ Common Mistakes to Avoid

❌ **Don't:** Create monolithic 400+ line README
✅ **Do:** Split into QUICK_REFERENCE (50 lines) + summaries + detailed

❌ **Don't:** Duplicate content across files
✅ **Do:** Link between tiers, maintain single source of truth

❌ **Don't:** Use inconsistent naming (status.md, summary.md, etc.)
✅ **Do:** Follow naming conventions (QUICK_REFERENCE, *_SUMMARY,*_FULL)

❌ **Don't:** Forget to update cross-references when adding new sections
✅ **Do:** Update README table and links immediately

❌ **Don't:** Let detailed/ grow beyond 1,000 lines
✅ **Do:** Split into multiple _FULL.md files per topic

---

## 🔄 Maintenance Policy

**Weekly:**

- Update QUICK_REFERENCE or QUICK_STATUS.md
- Archive completed items from summaries/

**Per Phase/Milestone:**

- Create new summary files as work completes
- Move summaries to detailed/ if historical

**Quarterly:**

- Audit context structure for consistency
- Refactor if any files exceed 1,000 lines
- Update this standards document if needed

---

## 📞 Questions?

See: `EXECUTION/spec/guides/runtime/CONTEXT_AWARE_USAGE.md`

For deep guidance on:

- How to structure specific context types
- Agent workflows with context
- Troubleshooting context issues
- Advanced optimization techniques

---

**Authority:** SDD v2.1 Framework Standards
**Version:** 1.0
**Status:** Production
**Last Updated:** April 19, 2026
**Maintainer:** Development Team
