# 🧠 Context Loading Strategy

## 🎯 Purpose

Define the global strategy for efficient context loading that respects token budgets while providing agents sufficient information.

---

## 🔒 Core Principle

> **Context is expensive. Load only what is required.**

Never load documentation "to be safe" — load strategically based on task classification.

---

## 🔁 Context Loading Process

### 1. Environment Detection

```bash
# Find governance config
cat .spec.config  # Workspace configuration
cat .providence/profile  # Workspace identity
```

### 2. Load Runtime Indices (ALWAYS)

```
.providence/source/search-keywords.md          # 5–10KB
.providence/source/spec-canonical-index.md     # 10–15KB
.providence/source/spec-guides-index.md        # 5–10KB
```

**Reason:** Indices are small and enable targeted lookups

### 3. Task Classification

Use [TASK_CLASSIFICATION.md](../decision-models/TASK_CLASSIFICATION.md) → Select PATH A–F

### 4. PATH-Specific Context Selection

Each PATH has a budget. Load ONLY what applies to your task:

- **PATH A (bug fix):** Single file + affected callers
- **PATH B (simple feature):** 1–2 modules + their dependencies
- **PATH C (complex):** Full cross-module graph
- **PATH D (parallel):** Per-thread isolation
- **PATH E (hotfix):** Minimal — production fix only
- **PATH F (refactor):** Code structure + related tests

### 5. Load Canonical (if needed for task)

```
docs/spec/canonical/core/mandates/       # Understand constraints
docs/spec/canonical/core/policies/       # Understand approval gates
docs/spec/canonical/core/rules/          # Understand style/testing
```

### 6. Load Guides (if you need HOW-TO)

```
docs/spec/canonical/specifications/      # If unsure how to implement
docs/guides/                              # If step-by-step help needed
```

### 7. Load Reality (ONLY if needed)

```
src/                                      # Read actual code
tests/                                    # Review existing tests
```

**When to load:** If indices/guides don't answer your question

---

## 📦 Context Layers (Priority Order)

```
1️⃣  Runtime Indices       (always — small, enables everything)
2️⃣  Task Classification   (always — determines what to load next)
3️⃣  Canonical             (if affected by rules/mandates)
4️⃣  Guides                (if you need HOW-TO)
5️⃣  Reality (code)        (only if indices/guides insufficient)
```

---

## ⚖️ Strategy: The 30/70 Rule

- **≤70% context:** Documentation, examples, guides
- **≥30% context:** Reasoning space for problem-solving

Never exceed 70% documentation utilization.

---

## 🎯 Decision Heuristic

**Before loading anything ask:**

1. ✅ Is this already in an index? → Use the index
2. ✅ Is this covered by my PATH budget? → Load it
3. ✅ Do I understand it from the summary? → Skip detailed read
4. ❌ Do I really need all 5 guides? → Load only the applicable one
5. ❌ Am I loading "to be safe"? → Rethink; probably don't

---

## 🚨 Anti-Patterns

| ❌ Anti-Pattern | ✅ Fix |
|---|---|
| "Load entire CANONICAL just in case" | Load only sections relevant to your PATH |
| Skipping indices and searching manually | Always start with indices first |
| Loading all guides when 1 guide applies | Use search-keywords to find the right guide |
| Using 60% budget on context, 10% on reasoning | Reserve 30%+ for thinking; use compression |
| Memorizing from previous session instead of loading current state | Always load .providence-cache.md at start |

---

## 📊 Typical Context Loads

### PATH A — Bug Fix

```
~40KB total:
- Indices (5KB)
- Relevant code (10KB)
- Affected layer spec (5KB)
- Tests for that module (5KB)
- Definition of Done checklist (1KB)
- Reserve for reasoning (9KB / 30% of 40KB)
```

### PATH C — Complex Feature

```
~85KB total:
- Indices (10KB)
- Architecture overview (10KB)
- 3+ module structures (20KB)
- Related specs (15KB)
- Tests across layers (15KB)
- Reserve for reasoning (15KB / ~18% of 85KB) ← compress if needed
```

---

## 🔧 Implementation

Load context via:

```bash
# Automated
providence ask "how do I implement a custom port?"  # Queries compiled governance

# Manual
# 1. Read search-keywords.md for topic
# 2. Follow pointer to relevant doc
# 3. Load that doc into context
# 4. Check budget via: providence runtime status
```

---

## 🔗 Related

- [TASK_CLASSIFICATION.md](../decision-models/TASK_CLASSIFICATION.md) — Detailed classification
- [path-routing.md](./path-routing.md) — PATH budgets and constraints
- [context-budget.md](./context-budget.md) — Budget calculation and zones
- [CONTEXT_SELECTION.md](../decision-models/CONTEXT_SELECTION.md) — Decision model for context choice
