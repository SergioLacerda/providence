# 📑 EXECUTION — Local Index

**Complete navigation for the EXECUTION flow (develop using SDD AGENT_HARNESS workflow)**

---

## 📍 Entry Points

Choose your starting point:

- **New to SDD?** → [CORE__START_HERE.md](./CORE__START_HERE.md) (5 min orientation)
- **Looking for specific doc?** → [NAVIGATION.md](./NAVIGATION.md) (keyword search)
- **Ready to implement?** → [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md) (7-phase workflow)
- **Something broken?** → [Emergency](.docs/spec/guides/emergency/) (5 crisis procedures)

---

## 🚀 AGENT_HARNESS: 7 Phases

The complete development workflow:

| Phase | Duration | Document | Goal |
|-------|----------|----------|------|
| **PHASE 0** | 20-30 min | [PHASE-0-AGENT-ONBOARDING.md](.docs/spec/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md) | Setup `.providence/` infrastructure (first time only) |
| **PHASE 1** | 15 min | [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md#phase-1) + [constitution.md](.docs/spec/canonical/rules/constitution.md) + [ia-rules.md](.docs/spec/canonical/rules/ia-rules.md) | Lock to rules, pass VALIDATION_QUIZ (≥80%) |
| **PHASE 2** | 5 min | [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md#phase-2) | Check execution state for conflicts |
| **PHASE 3** | 5 min | [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md#phase-3) | Choose PATH (A/B/C/D) → load right docs |
| **PHASE 4** | 10-20 min | [search-keywords.md](.docs/spec/runtime/search-keywords.md) + [spec-guides-index.md](.docs/spec/runtime/spec-guides-index.md) | Load context on-demand |
| **PHASE 5** | 1-8 hours | [CANONICAL/specifications/](.docs/spec/canonical/specifications/) | Implement + tests (TDD) |
| **PHASE 6** | 10-15 min | [definition-of-done.md](.docs/spec/canonical/specifications/definition-of-done.md) | Validate (tests + quality gate) |
| **PHASE 7** | 10 min | [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md#phase-7) | Checkpoint + PR |

---

## 📚 Documentation Structure

### 🔴 Constitutional Layer (Immutable)

- [constitution.md](.docs/spec/canonical/rules/constitution.md) — 15 immutable principles
- Status: Read once, never changes

### 🟠 Rules Layer (Mandatory)

- [ia-rules.md](.docs/spec/canonical/rules/ia-rules.md) — 16 mandatory rules
- [conventions.md](.docs/spec/canonical/rules/conventions.md) — Naming, structure, patterns
- Status: Must follow for every implementation

### 🟡 Architecture Layer (Decisions)

- [ADR-001-autonomous-agents.md](.docs/spec/canonical/decisions/ADR-001-autonomous-agents.md)
- [ADR-002-three-layer-architecture.md](.docs/spec/canonical/decisions/ADR-002-three-layer-architecture.md)
- [ADR-003-ports-adapters-pattern.md](.docs/spec/canonical/decisions/ADR-003-ports-adapters-pattern.md)
- [ADR-004-isolated-testing.md](.docs/spec/canonical/decisions/ADR-004-isolated-testing.md)
- [ADR-005-thread-isolation-mandatory.md](.docs/spec/canonical/decisions/ADR-005-thread-isolation-mandatory.md)
- [ADR-006-governance-automation.md](.docs/spec/canonical/decisions/ADR-006-governance-automation.md)
- Status: Reference when designing or questioning decisions

### 🟢 Specifications Layer (How To)

- [architecture.md](.docs/spec/canonical/specifications/architecture.md) — Overall structure
- [testing.md](.docs/spec/canonical/specifications/testing.md) — Test patterns & TDD
- [feature-checklist.md](.docs/spec/canonical/specifications/feature-checklist.md) — Quality gate
- [definition-of-done.md](.docs/spec/canonical/specifications/definition-of-done.md) — 45+ completion criteria
- [communication.md](.docs/spec/canonical/specifications/communication.md) — Docs & clarity
- Status: Follow during PHASE 5 implementation

### 🔵 Guides Layer (How To Do)

**Onboarding:**

- [PHASE-0-AGENT-ONBOARDING.md](.docs/spec/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md)
- [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md)

**Operational:**

- [DEVELOPMENT_WORKFLOW_VALIDATION.md](.docs/spec/guides/operational/DEVELOPMENT_WORKFLOW_VALIDATION.md)
- [METRICS_TRACKING.md](.docs/spec/guides/operational/METRICS_TRACKING.md)
- [PRE_COMMIT_HOOKS.md](.docs/spec/guides/operational/PRE_COMMIT_HOOKS.md)

**Emergency (Crisis Procedures):**

- [README.md](.docs/spec/guides/emergency/README.md) — Pick your emergency
- [PRE_COMMIT_HOOK_FAILURE.md](.docs/spec/guides/emergency/PRE_COMMIT_HOOK_FAILURE.md)
- [TEST_FAILURE_GUIDE.md](.docs/spec/guides/emergency/TEST_FAILURE_GUIDE.md)
- [RULES_VIOLATION_DETECTED.md](.docs/spec/guides/emergency/RULES_VIOLATION_DETECTED.md)
- [IMPORTS_CORRUPTED.md](.docs/spec/guides/emergency/IMPORTS_CORRUPTED.md)
- [METRICS_CORRUPTION_RECOVERY.md](.docs/spec/guides/emergency/METRICS_CORRUPTION_RECOVERY.md)

**Reference:**

- [FAQ.md](.docs/spec/guides/reference/FAQ.md) — Common questions
- [GLOSSARY.md](.docs/spec/guides/reference/GLOSSARY.md) — Terminology
- [HOW_EACH_LAYER_WORKS.md](.docs/spec/guides/reference/HOW_EACH_LAYER_WORKS.md) — Deep dives

### 🟣 Runtime Layer (Search Indices)

- [search-keywords.md](.docs/spec/runtime/search-keywords.md) — Find docs by topic
- [spec-canonical-index.md](.docs/spec/runtime/spec-canonical-index.md) — CANONICAL/ docs
- [spec-guides-index.md](.docs/spec/runtime/spec-guides-index.md) — guides/ docs

### ⚫ Custom / Project Layer

- `docs/ia/custom/[YOUR_PROJECT]/` — Project-specific specs + execution state

---

## 🔍 Find by Task

| I want to... | Read this |
|--------------|-----------|
| Understand what SDD is | [constitution.md](.docs/spec/canonical/rules/constitution.md) (5 min) |
| Pass the VALIDATION_QUIZ | [ia-rules.md](.docs/spec/canonical/rules/ia-rules.md) (must get ≥80%) |
| Implement a feature | [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md) → PHASE 5 |
| Fix a bug | [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md) → PATH A |
| Write tests | [testing.md](.docs/spec/canonical/specifications/testing.md) |
| Check my work | [definition-of-done.md](.docs/spec/canonical/specifications/definition-of-done.md) |
| Understand architecture | [architecture.md](.docs/spec/canonical/specifications/architecture.md) |
| Ask a question | [FAQ.md](.docs/spec/guides/reference/FAQ.md) |
| Find a specific doc | [NAVIGATION.md](./NAVIGATION.md) (keyword search) |
| Emergency | [Emergency/README.md](.docs/spec/guides/emergency/README.md) |

---

## 🧭 By Role

**👨‍💻 Individual Contributor / Developer**

```
_START_HERE.md
  ↓
AGENT_HARNESS.md (PHASE 1-7)
  ↓
CANONICAL/specifications/
  ↓
Implement + tests
```

**🤖 AI Agent / Automation**

```
PHASE-0-AGENT-ONBOARDING.md (setup)
  ↓
ia-rules.md (must pass ≥80%)
  ↓
AGENT_HARNESS.md (full workflow)
  ↓
Implement
```

**🆘 Someone in Crisis**

```
Emergency/README.md
  ↓
Pick specific crisis guide
  ↓
Follow steps
```

---

## ✅ Success Criteria

| Goal | Success = |
|------|-----------|
| Feature implemented | Code written + committed |
| Tests passing | 100% coverage for new code |
| Quality gate | Definition of done (45+ items) checked |
| Knowledge captured | `.providence/context-aware/` docs updated |
| Ready for review | PR with checkpoint + decisions documented |

---

## 🚀 Next Steps

1. **New?** → [CORE__START_HERE.md](./CORE__START_HERE.md)
2. **Ready to code?** → [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md)
3. **Specific question?** → [NAVIGATION.md](./NAVIGATION.md)
4. **In trouble?** → [Emergency/README.md](.docs/spec/guides/emergency/README.md)

---

**Purpose:** EXECUTION flow index
**Target:** Developers/agents using workflow
**Status:** Ready
**Last updated:** April 19, 2026
