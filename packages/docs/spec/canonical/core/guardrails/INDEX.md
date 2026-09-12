# Guardrail System: Governance Levels

**Purpose:** Enforce governance at different stages of the development lifecycle to prevent drift and technical debt.

---

## 🏗️ Guardrail Levels

### Level 1: Semantic & Structural (Static)

*Focus: Is the system organized correctly?*

- **Constraint**: Every new module must have a corresponding entry in `indices/`.
- **Constraint**: No orphan files in `docs/` (must be indexed).
- **Mechanism**: Index Linting.

### Level 2: Operational & Git (Dynamic)

*Focus: Is the process being followed?*

- **Constraint**: `.providence-cache.md` must be updated before any commit.
- **Constraint**: `mandate.spec` must pass validation.
- **Mechanism**: [pre-commit](../../../../../tools/scripts/git-hooks/pre-commit) (Git Hooks).

### Level 3: Cognitive & Integrity (Intelligence)

*Focus: Is the reasoning quality high?*

- **Constraint**: Agent must pass the "Two-Question Quiz" before research.
- **Constraint**: READMEs must follow the "Honest Critique" policy.
- **Mechanism**: Decision Models & Quizzes.

---

## 🚦 Enforcement Matrix

| Level | Severity | Action on Violation |
|---|---|---|
| **L1** | Warning | Log warning + request index update |
| **L2** | Error | Block Commit / Block Merge |
| **L3** | Critical | Halt Execution + Request Human Review |

---

## 🔗 References

- Git Hooks: [`../../../../../tools/scripts/git-hooks/pre-commit`](../../../../../tools/scripts/git-hooks/pre-commit)
- Honest Critique: [`../policies/P002_HONEST_CRITIQUE.md`](../policies/P002_HONEST_CRITIQUE.md)
