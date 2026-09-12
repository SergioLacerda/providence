# 📚 Guides Layer Index

**Complete reference to operational guides and instructions**

---

## 🎯 Purpose

Guides provide step-by-step help for specific scenarios. Use when you need "how do I..." or "what do I do when..."

---

## 📖 Onboarding Guides

For new developers and agents learning SDD.

### AGENT_HARNESS: Complete 7-Phase Workflow

**File:** `guides/onboarding/AGENT_HARNESS.md`
**Purpose:** Full explanation of all 7 phases
**Read When:** First time understanding the workflow
**Duration:** 20-30 minutes
**Covers:** PHASE 0-7 with entry points, duration, requirements

### PHASE-0-AGENT-ONBOARDING

**File:** `guides/onboarding/PHASE-0-AGENT-ONBOARDING.md`
**Purpose:** Detailed guide for Phase 0 setup
**Read When:** New to SDD, need to set up .providence/ infrastructure
**Duration:** 20-30 minutes
**Covers:** Creating context-aware and runtime directories, validating setup

### Entry Points by Tool

**File:** `guides/onboarding/ENTRY_POINTS_BY_TOOL.md`
**Purpose:** Where to start based on your IDE/environment
**Read When:** Getting started with specific tool (Copilot, Cursor, etc.)
**Covers:** Copilot Chat, VS Code, Cursor IDE, Terminal entry points

### VALIDATION_QUIZ

**File:** `guides/onboarding/VALIDATION_QUIZ.md`
**Purpose:** 8-10 questions testing SDD knowledge
**Read When:** After learning rules, before implementing
**Required:** Must pass ≥80% before PHASE 5
**Covers:** Constitution, rules, key decisions

### Development Workflow Validation

**File:** `guides/onboarding/DEVELOPMENT_WORKFLOW_VALIDATION.md`
**Purpose:** How to validate your workflow is correct
**Read When:** Want to verify you're following SDD properly
**Duration:** 5-10 minutes
**Covers:** Checklist for workflow validation

### Onboarding Consolidation

**File:** `guides/onboarding/ONBOARDING_CONSOLIDATION.md`
**Purpose:** Summary of all onboarding steps
**Read When:** Quick reference after full onboarding
**Covers:** Consolidated checklist

### Phase 7 Validation

**File:** `guides/onboarding/PHASE-7-VALIDATION.md`
**Purpose:** Detailed guide for final validation phase
**Read When:** About to checkpoint your work
**Covers:** PHASE 7 checklist and requirements

### Session Quick Reference

**File:** `guides/onboarding/SESSION_QUICK_REFERENCE.md`
**Purpose:** One-page reference for quick lookup
**Read When:** Searching for quick answers during session
**Covers:** Common questions and answers

### Implementation Notes

**File:** `guides/onboarding/IMPLEMENTATION_NOTES.md`
**Purpose:** Notes on implementing SDD framework
**Read When:** Understanding implementation details
**Covers:** Technical implementation details

---

## 🔧 Operational Guides

For day-to-day operations and specific scenarios.

### Adding New Project

**File:** `guides/operational/ADDING_NEW_PROJECT.md`
**Purpose:** Step-by-step guide for integrating a new project
**Read When:** Onboarding a new project to SDD
**Duration:** 30 minutes
**Covers:** Integration steps, template copying, validation

### Handling Merge Conflicts in Docs

**File:** `guides/operational/HANDLING_MERGE_CONFLICTS_IN_DOCS.md`
**Purpose:** Resolving conflicts in documentation files
**Read When:** Documentation merge conflicts occur
**Covers:** Conflict resolution strategies, prevention

### Migrating Docs Between Projects

**File:** `guides/operational/MIGRATING_DOCS_BETWEEN_PROJECTS.md`
**Purpose:** Moving documentation across projects
**Read When:** Centralizing or reorganizing docs
**Covers:** Migration procedures, verification steps

### Revoking Deprecated Rules

**File:** `guides/operational/REVOKING_DEPRECATED_RULES.md`
**Purpose:** How to formally deprecate and remove old rules
**Read When:** Updating SDD framework rules
**Duration:** 15-20 minutes
**Covers:** Deprecation process, voting, removal

### Troubleshooting Spec Violations

**File:** `guides/operational/TROUBLESHOOTING_SPEC_VIOLATIONS.md`
**Purpose:** Diagnosing and fixing framework violations
**Read When:** CI/CD fails or rule violations detected
**Covers:** Common violations, fixes, prevention

---

## 🚨 Emergency Guides

For when things go wrong.

### Emergency Overview

**File:** `guides/emergency/README.md`
**Purpose:** What to do when framework is broken
**Read When:** Something critical fails
**Covers:** Emergency procedures, recovery strategies

### Auto-Fix Corruption Recovery

**File:** `guides/emergency/AUTO_FIX_CORRUPTION_RECOVERY.md`
**Purpose:** Recovering from corrupted files
**Read When:** Framework files are damaged or inconsistent
**Covers:** Detection, backup recovery, validation

### Canonical Corruption Recovery

**File:** `guides/emergency/CANONICAL_CORRUPTION_RECOVERY.md`
**Purpose:** Recovering when CANONICAL layer is broken
**Read When:** Constitution or core rules corrupted
**Covers:** Recovery procedures, validation

### CI/CD Gate Failure

**File:** `guides/emergency/CI_CD_GATE_FAILURE.md`
**Purpose:** All PRs blocked by CI/CD gates
**Read When:** CI/CD is completely broken
**Covers:** Diagnosis, emergency bypass, remediation

### Metrics Corruption Recovery

**File:** `guides/emergency/METRICS_CORRUPTION_RECOVERY.md`
**Purpose:** Recovering from corrupted metrics
**Read When:** Metrics have impossible values
**Covers:** Detection, recalculation, validation

### Pre-Commit Hook Failure

**File:** `guides/emergency/PRE_COMMIT_HOOK_FAILURE.md`
**Purpose:** When pre-commit hooks fail
**Read When:** Git hooks aren't running or blocking commits
**Covers:** Diagnosis, repair, re-enabling

---

## 🗺️ Quick Navigation

### By Scenario

**"I'm brand new to SDD"**

1. Read: `AGENT_HARNESS.md` (understand phases)
2. Read: `PHASE-0-AGENT-ONBOARDING.md` (set up)
3. Take: `VALIDATION_QUIZ.md` (test knowledge)

**"I'm implementing a feature"**

1. Read: `AGENT_HARNESS.md` (phases 1-7)
2. Reference: `VALIDATION_QUIZ.md` if confused on rules
3. Use: `DEVELOPMENT_WORKFLOW_VALIDATION.md` (verify process)

**"I'm adding a new project"**
→ `ADDING_NEW_PROJECT.md` (30-min process)

**"Something is broken"**
→ `guides/emergency/README.md` (troubleshooting)

**"I need quick answers"**
→ `SESSION_QUICK_REFERENCE.md` (one-page lookup)

**"I need to organize my context"**
→ `CANONICAL/specifications/context-aware-agent-pattern.md` (canonical pattern)

### By Duration

**5 minutes:**

- SESSION_QUICK_REFERENCE.md
- ENTRY_POINTS_BY_TOOL.md
- VALIDATION_QUIZ.md (answer only, don't learn)

**15-20 minutes:**

- ONBOARDING_CONSOLIDATION.md
- DEVELOPMENT_WORKFLOW_VALIDATION.md
- TROUBLESHOOTING_SPEC_VIOLATIONS.md

**20-30 minutes:**

- AGENT_HARNESS.md (full read)
- PHASE-0-AGENT-ONBOARDING.md
- ADDING_NEW_PROJECT.md

**On-demand:**

- Emergency guides (when needed)
- Operational guides (specific scenarios)

---

## 📊 Guide Relationships

```
PHASE 0: Setup
    ↓ (read PHASE-0-AGENT-ONBOARDING.md)
PHASE 1-7: Workflow
    ↓ (read AGENT_HARNESS.md)
Quiz: Knowledge Check
    ↓ (take VALIDATION_QUIZ.md)
Operations: Ongoing
    ├── Adding projects? → ADDING_NEW_PROJECT.md
    ├── Conflicts? → HANDLING_MERGE_CONFLICTS_IN_DOCS.md
    ├── Moving docs? → MIGRATING_DOCS_BETWEEN_PROJECTS.md
    ├── Updating rules? → REVOKING_DEPRECATED_RULES.md
    └── Violations? → TROUBLESHOOTING_SPEC_VIOLATIONS.md
Emergency: When broken
    └── See: guides/emergency/README.md
```

---

## ⚡ Quick Links by Problem

| Problem | Solution |
|---------|----------|
| Don't know where to start | `ENTRY_POINTS_BY_TOOL.md` |
| Don't understand phases | `AGENT_HARNESS.md` |
| Need to set up | `PHASE-0-AGENT-ONBOARDING.md` |
| Need to validate knowledge | `VALIDATION_QUIZ.md` |
| Need to verify my workflow | `DEVELOPMENT_WORKFLOW_VALIDATION.md` |
| Adding new project | `ADDING_NEW_PROJECT.md` |
| Git conflicts | `HANDLING_MERGE_CONFLICTS_IN_DOCS.md` |
| Framework broken | `guides/emergency/README.md` |
| Need quick answer | `SESSION_QUICK_REFERENCE.md` |
| Need to organize context | `CANONICAL/specifications/context-aware-agent-pattern.md` |

---

**For complete SDD docs:** [NAVIGATION.md](../../../NAVIGATION.md)
**For search by keywords:** [search-keywords.md](../indices/search-keywords.md)
**For CANONICAL layer:** [spec-canonical-index.md](../indices/spec-canonical-index.md)
**Last Updated:** April 19, 2026
