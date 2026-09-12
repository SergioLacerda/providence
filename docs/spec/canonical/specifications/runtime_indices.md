# ⚡ Runtime Indices Specification

**Authority:** SPEC v2.1 (Immutable Specification)
**Status:** Mandatory for all projects
**Location:** Framework templates at `docs/indices/`
**Project Copies:** `.providence/source/` (each project)
**Updated:** April 19, 2026

---

## 🎯 Purpose

Specify the 3 runtime indices that agents create during PHASE 0 to enable efficient document discovery and context awareness.

**Key Insight:** Agents shouldn't spend time finding docs; indices make everything searchable.

---

## 📌 Two-Tier Index System

### Framework Tier

**Location:** `docs/indices/`
**Files:**

- `spec-canonical-index.md` — Reference to all CANONICAL docs
- `spec-guides-index.md` — Reference to all operational guides
- `search-keywords.md` — Keyword-to-document mapping
- `_INDEX.md` — This layer's purpose and structure

**Purpose:** Templates for projects to copy and customize
**Updated:** Quarterly (when framework changes)
**Audience:** All projects (reference templates)

### Project Tier

**Location:** `.providence/source/` (in each project)
**Files:** Same names as framework tier
**Purpose:** Each project maintains its own runtime indices
**Updated:** Per-project basis (can diverge from framework)
**Audience:** Project-specific usage

### How It Works

```
1. SPEC framework provides template indices at docs/indices/
2. During project initialization (PHASE 0), templates copied to .providence/source/
3. Projects customize their indices as needed
4. Framework indices serve as reference defaults
```

---

## 📇 Three Required Indices

### Index 1: spec-canonical-index.md

**Purpose:** Quick reference to all CANONICAL authority documents
**Framework Location:** `docs/indices/spec-canonical-index.md`
**Project Location:** `.providence/source/spec-canonical-index.md`
**Created by:** PHASE 0 automation
**Updated:** Quarterly (when CANONICAL changes)

**Contents:**

- Authority hierarchy (constitution → rules → decisions → specs)
- Constitution overview (15 immutable principles)
- Mandatory Rules (16 total with descriptions)
- Conventions (code style, naming, format)
- Architecture Decisions (6 ADRs with rationale)
- Specifications (context-aware, definition-of-done, communication)
- Quick navigation by need
- Emergency quick links

**Key Sections:**

1. Introduction (purpose + links)
2. Rules layer (constitution, rules, conventions)
3. Decisions layer (ADR-001 through ADR-006)
4. Specifications layer (how-to guides)
5. Search mapping (keyword → file)
6. Reading paths (by use case)

**Purpose:** When agent asks "where are the rules?", they read this index.

---

### Index 2: spec-guides-index.md

**Purpose:** Quick reference to all operational guides
**Framework Location:** `docs/indices/spec-guides-index.md`
**Project Location:** `.providence/source/spec-guides-index.md`
**Created by:** PHASE 0 automation
**Updated:** Monthly (when guides added/changed)

**Contents:**

- Onboarding guides (AGENT_HARNESS, PHASE-0, validation, etc.)
- Operational guides (adding projects, conflicts, migration, etc.)
- Emergency guides (6 runbooks for failures)
- Reference guides (FAQ, glossary, how-each-layer-works)
- Quick navigation by scenario
- Duration estimates per guide
- Guide relationships and dependencies

**Key Sections:**

1. Onboarding guides (9 files)
2. Operational guides (5 files)
3. Emergency guides (6 files)
4. Reference guides (4 files)
5. Quick navigation by scenario/duration
6. Guide relationships

**Purpose:** When agent asks "how do I...?", they find answer here.

---

### Index 3: search-keywords.md

**Purpose:** Keyword-to-document mapping for on-demand discovery
**Framework Location:** `docs/indices/search-keywords.md`
**Project Location:** `.providence/source/search-keywords.md`
**Created by:** PHASE 0 automation
**Updated:** As new patterns emerge

**Contents:**

- Framework concepts table
- Constitutional foundation table
- Architecture decisions table
- Context-aware patterns table
- Implementation standards table
- Development workflow table
- Emergency procedures table
- Reference & glossary table
- Quick navigation guide
- By-task-type scenarios

**Key Sections:**

1. Keyword mappings (organized by topic)
2. Common scenarios (keyword → solution)
3. By task type (implementing, help, broken, projects, learning)
4. Pro tips
5. Update guidance

**Purpose:** When agent asks "where do I find [concept]?", they search this.

---

## 🚀 PHASE 0: Creating Runtime Indices

### Step 1: Check Framework Indices Exist

```bash
# Verify framework indices present
ls -la docs/indices/
# Expected:
# spec-canonical-index.md
# spec-guides-index.md
# search-keywords.md
# _INDEX.md
```

### Step 2: Copy to Project

**Automated Approach (Recommended):**

```bash
# In PHASE 0 automation script:
SPEC_PATH=$(grep spec_path .spec.config | cut -d' ' -f3)

# Create .providence/source if needed
mkdir -p .providence/source/

# Copy indices templates
cp $SPEC_PATH/docs/indices/*.md .providence/source/

echo "✅ Runtime indices initialized"
```

**Manual Approach:**

```bash
# Copy templates one by one
cp docs/indices/search-keywords.md .providence/source/
cp docs/indices/spec-canonical-index.md .providence/source/
cp docs/indices/spec-guides-index.md .providence/source/

# Verify copied
ls -la .providence/source/
```

### Step 3: Verify Setup

```bash
# Check all 3 exist
[ -f .providence/source/spec-canonical-index.md ] && echo "✅ CANONICAL index"
[ -f .providence/source/spec-guides-index.md ] && echo "✅ Guides index"
[ -f .providence/source/search-keywords.md ] && echo "✅ Keywords index"

# Verify they have content
wc -l .providence/source/*.md
# Expected: each > 50 lines
```

---

## 🔄 Using Runtime Indices

### Scenario 1: Finding a Rule

```
Agent: "Where's the rule about testing?"

1. Agent opens: .providence/source/search-keywords.md
2. Search for: "testing"
3. Find: CANONICAL/specifications/definition_of_done.md
4. Read: Testing section
```

### Scenario 2: Finding a Guide

```
Agent: "How do I add a new project?"

1. Agent opens: .providence/source/spec-guides-index.md
2. Search for: "Adding new project"
3. Find: guides/operational/ADDING_NEW_PROJECT.md
4. Follow: Step-by-step instructions
```

### Scenario 3: Understanding a Decision

```
Agent: "Why is thread isolation mandatory?"

1. Agent opens: .providence/source/spec-canonical-index.md
2. Search for: "thread isolation"
3. Find: CANONICAL/decisions/ADR-005
4. Read: Architecture decision and rationale
```

---

## ✅ Verification Checklist

**After PHASE 0, verify indices are complete:**

```bash
# ✅ All 3 files exist
ls .providence/source/search-keywords.md && echo "✅"
ls .providence/source/spec-canonical-index.md && echo "✅"
ls .providence/source/spec-guides-index.md && echo "✅"

# ✅ Each has substantial content (> 50 lines)
[ $(wc -l < .providence/source/search-keywords.md) -gt 50 ] && echo "✅"
[ $(wc -l < .providence/source/spec-canonical-index.md) -gt 50 ] && echo "✅"
[ $(wc -l < .providence/source/spec-guides-index.md) -gt 50 ] && echo "✅"

# ✅ Links point to real files
grep "core/mandates/" .providence/source/spec-canonical-index.md && echo "✅"

# ✅ Can read them
head -20 .providence/source/search-keywords.md && echo "✅"
```

---

## 📈 Maintenance

### Weekly

No maintenance needed. Indices are read-only after creation.

### Monthly

- Check if new guides added to SPEC → update .providence/source/ copies
- Check if new patterns discovered → add keywords
- Commit updates in regular checkpoints

### Quarterly

- Re-generate indices from framework templates if SPEC changed
- Verify all links still valid
- Update reading paths if documentation changed
- Commit: "docs: update runtime indices per SPEC v2.1.X"

---

## 🔄 Update Cycle

### When SPEC Framework Updates

```
1. SPEC changes (new ADR, guide, spec, etc.)
2. Framework updates: docs/indices/
3. Projects should re-copy during PHASE re-validation
4. Each project: cp docs/indices/* .providence/source/
5. Projects customize .providence/source/ for project-specific needs
```

### When New Patterns Discovered

```
1. Agent discovers new keyword/pattern during work
2. Adds to .providence/source/search-keywords.md (project-local)
3. Documents which file teaches this pattern
4. Commits in regular checkpoint
5. Next agent benefits from discovery (project-local knowledge)
```

---

## 🎯 Success Criteria

Indices are working correctly if:

✅ **Discoverability:** Agent asks question → finds answer in < 2 min
✅ **Accuracy:** All links point to correct documents
✅ **Completeness:** All CANONICAL docs indexed, all guides indexed
✅ **Freshness:** Framework indices updated quarterly
✅ **Usability:** Clear keyword mapping, easy navigation
✅ **Customization:** Projects maintain own .providence/source/ versions

---

## 📚 Related Specifications

- [Agent Entrypoint](../core/generated/AGENT_ENTRYPOINT.md) — Agent context organization
- [Context Loading Strategy](../core/cognition/context-loading/) — Full PHASE 0 context loading
- [Architecture Specification](./architecture.md) — Framework layers and design
- [Indices Overview](../../../indices/_INDEX.md) — Indices layer overview

---

## ✨ Why Indices Matter

### Without Indices (Before PHASE 0)

```
Agent: "Where do I find the rules?"
→ Agent searches for docs
→ Agent reads 5 README files
→ Agent navigates docs/ia folder
→ Takes 30+ minutes to find answers
→ Wastes time, gets frustrated
```

### With Indices (After PHASE 0)

```
Agent: "Where do I find the rules?"
→ Agent opens .providence/source/search-keywords.md
→ Searches "rules" in file
→ Finds: ia-rules.md in CANONICAL/rules/
→ Takes 1 minute to find answer
→ Saved 29 minutes × 100 uses = 2900 hours/year
```

---

## 🎓 Common Questions

**Q: Can projects modify their .providence/source/ indices?**
A: Yes! Each project customizes for its needs. Just don't break links to framework docs.

**Q: How often are framework indices (docs/indices/) updated?**
A: Quarterly, when SPEC framework changes significantly.

**Q: What if a project's .providence/source/ gets out of sync with framework?**
A: Normal. Projects diverge. Re-sync during quarterly SPEC updates or use: `cp docs/indices/* .providence/source/`

**Q: Who maintains the indices?**
A: Automated scripts in PHASE 0; then projects maintain their own .providence/source/ copies.

---

**Authority:** SPEC v2.1 Specification (CANONICAL)
**Status:** Mandatory for all projects
**Effective Date:** April 19, 2026
**Last Updated:** April 19, 2026
