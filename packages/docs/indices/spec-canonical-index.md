# Canonical Index

Complete reference to immutable authority layer in `docs/spec/canonical/`. These are the source-of-truth specs that govern all work.

---

## 🔒 Core Governance Kernel

**Location:** `docs/spec/canonical/core/`

### 📋 Mandates (HARD)

Immutable governance rules enforced at runtime.

| Mandate | Purpose |
|---|---|
| [M003: Context Awareness](../spec/canonical/core/mandates/M003_CONTEXT_AWARENESS.md) | Maintain `.providence-cache.md` per project with execution state |
| [M005: Token Economy](../spec/canonical/core/mandates/M005_TOKEN_ECONOMY.md) | Enforce budget zones (GREEN/YELLOW/RED/BREACH) per PATH |
| [M007: Telemetry](../spec/canonical/core/mandates/M007_TELEMETRY.md) | Emit mandatory governance events every session |

### 📌 Policies (IMMUTABLE)

Always-active behavioral policies.

| Policy | Purpose |
|---|---|
| [P001: Project Boundary](../spec/canonical/core/policies/P001_PROJECT_BOUNDARY.md) | Namespace isolation — govern by workspace profile |
| [P002: Honest Critique](../spec/canonical/core/policies/P002_HONEST_CRITIQUE.md) | Truth in labeling, debt-aware reporting |
| [P003: Mandatory Human Review](../spec/canonical/core/policies/P003_MANDATORY_HUMAN_REVIEW.md) | Agents propose, humans dispose — no autonomous git mutations |
| [P004: Pre-Delivery Quality Gate](../spec/canonical/core/policies/P004_PRE_DELIVERY_QUALITY_GATE.md) | Verify tooling present, run mandatory tools, report status |

### 🧠 Cognition Module

Decision engines for task classification, context loading, and anti-pattern avoidance.

**Decision Models:**

- [TASK_CLASSIFICATION.md](../spec/canonical/core/cognition/decision-models/TASK_CLASSIFICATION.md) — Route task to PATH A–F
- [CONTEXT_SELECTION.md](../spec/canonical/core/cognition/decision-models/CONTEXT_SELECTION.md) — Select minimal context per task
- [EXECUTION_DECISION.md](../spec/canonical/core/cognition/decision-models/EXECUTION_DECISION.md) — Deterministic vs Guided vs Exploratory

**Context Loading:**

- [context-budget.md](../spec/canonical/core/cognition/context-loading/context-budget.md) — Budget targets per PATH
- [path-routing.md](../spec/canonical/core/cognition/context-loading/path-routing.md) — Full routing table: task → PATH → docs
- [strategy.md](../spec/canonical/core/cognition/context-loading/strategy.md) — Priority order: Runtime → Canonical → Guides → Reality

**Anti-Patterns:**

- [CONTEXT_IGNORANCE.md](../spec/canonical/core/cognition/anti-patterns/CONTEXT_IGNORANCE.md) — Loading no runtime context
- [OVERLOADING_CONTEXT.md](../spec/canonical/core/cognition/anti-patterns/OVERLOADING_CONTEXT.md) — Loading too much, exceeding budget
- [RULE_BYPASS.md](../spec/canonical/core/cognition/anti-patterns/RULE_BYPASS.md) — Hacking around mandates/policies
- [STATE_DESYNC.md](../spec/canonical/core/cognition/anti-patterns/STATE_DESYNC.md) — Operating on stale state

### 💰 Economy Module

Token and resource budget enforcement.

| Document | Purpose |
|---|---|
| [efficiency-policy.md](../spec/canonical/core/economy/efficiency-policy.md) | Compression obligations, provider chain, circuit breakers |
| [execution-budget.md](../spec/canonical/core/economy/execution-budget.md) | Hard ceilings per PATH, zone table, re-baselining |
| [metrics.md](../spec/canonical/core/economy/metrics.md) | KPI definitions, telemetry field specs |

### 🔔 Telemetry Module

Compliance and observability events.

| Document | Purpose |
|---|---|
| [governance-events.md](../spec/canonical/core/telemetry/governance-events.md) | Event schema: drift, violation, policy failure |

### ⚔️ Guardrails Module

Three-level enforcement: Structural (L1), Operational (L2), Cognitive (L3).

- [guardrails/INDEX.md](../spec/canonical/core/guardrails/INDEX.md) — Guardrail levels and enforcement matrix

### 🎯 Rules

Hard style, testing, and structure rules.

| Rule | Purpose |
|---|---|
| [code-style.md](../spec/canonical/core/rules/code-style.md) | Code naming and organization |
| [tests.md](../spec/canonical/core/rules/tests.md) | Test requirements, F.I.R.S.T principles, mocking rules |
| [dependencies.md](../spec/canonical/core/rules/dependencies.md) | Dependency declaration and resolution |
| [structure.md](../spec/canonical/core/rules/structure.md) | Module organization and layer boundaries |
| [formatting.md](../spec/canonical/core/rules/formatting.md) | Code formatting conventions |
| [logging.md](../spec/canonical/core/rules/logging.md) | Logging standards and patterns |

### 🤖 Generated / Runtime

Compiled execution layer.

| Document | Purpose |
|---|---|
| [generated/AGENT_ENTRYPOINT.md](../spec/canonical/core/generated/AGENT_ENTRYPOINT.md) | 10-step agent bootstrap and execution kernel |
| [generated/HANDSHAKE.md](../spec/canonical/core/generated/HANDSHAKE.md) | 5-step governance activation handshake |
| [generated/AGENT_RUNTIME_PROTOCOL.md](../spec/canonical/core/generated/AGENT_RUNTIME_PROTOCOL.md) | 5-step execution contract |

---

## 📚 Specifications

How-to and architectural guidance.

**Location:** `docs/spec/canonical/specifications/`

| Specification | Purpose |
|---|---|
| [architecture.md](../spec/canonical/specifications/architecture.md) | 8-layer Clean Architecture design (Python) |
| [communication.md](../spec/canonical/specifications/communication.md) | Checkpoint format, code comment philosophy, ADR references |
| [compiler_design.md](../spec/canonical/specifications/compiler_design.md) | DSL compiler pipeline, msgpack encoding, token reduction |
| [compliance.md](../spec/canonical/specifications/compliance.md) | Quality gates, test coverage, CI/CD compliance |
| [contracts.md](../spec/canonical/specifications/contracts.md) | Port interface standards, Adapter contracts |
| [definition_of_done.md](../spec/canonical/specifications/definition_of_done.md) | Merge validation checklist (8 categories) |
| [feature-checklist.md](../spec/canonical/specifications/feature-checklist.md) | Step-by-step feature implementation through 8 layers |
| [observability.md](../spec/canonical/specifications/observability.md) | Logging, tracing, metrics, on-call model |
| [performance.md](../spec/canonical/specifications/performance.md) | SLO targets, latency budgets, availability targets |
| [PERFORMANCE_TESTING_GUIDE.md](../spec/canonical/specifications/PERFORMANCE_TESTING_GUIDE.md) | How to run and interpret performance tests |
| [runtime_indices.md](../spec/canonical/specifications/runtime_indices.md) | Two-tier index system specification |
| [security-model.md](../spec/canonical/specifications/security-model.md) | Threat model, auth/authz, data protection, compliance |
| [testing.md](../spec/canonical/specifications/testing.md) | Golden Rule: never alter production code for tests; layer-specific strategy |

---

## 🏗️ Features

Framework capabilities and adoption models.

**Location:** `docs/spec/canonical/features/`

Examples (not exhaustive):

- CLEAN_ARCHITECTURE — 8-layer domain/application/infrastructure split
- TDD — Test-First development mandate
- TELEMETRY_AUDIT — Mandatory event logging
- TOKEN_ECONOMY — Budget-aware execution

---

## 📖 Architecture Decisions

Strategic decisions and trade-offs.

**Location:** `docs/spec/decisions/`

Examples (ADR-001 through ADR-010 + DECISIONS_APRIL_2026)

---

## 🔗 Navigation by Need

**"I need to understand..."**

| Need | Start Here |
|---|---|
| How to classify my task | [TASK_CLASSIFICATION.md](../spec/canonical/core/cognition/decision-models/TASK_CLASSIFICATION.md) |
| What context to load | [context-budget.md](../spec/canonical/core/cognition/context-loading/context-budget.md) |
| How to structure code | [architecture.md](../spec/canonical/specifications/architecture.md) |
| What makes code merge-ready | [definition_of_done.md](../spec/canonical/specifications/definition_of_done.md) |
| What tests I must write | [testing.md](../spec/canonical/specifications/testing.md) |
| What's a policy violation | [P002](../spec/canonical/core/policies/P002_HONEST_CRITIQUE.md), [P003](../spec/canonical/core/policies/P003_MANDATORY_HUMAN_REVIEW.md), [P004](../spec/canonical/core/policies/P004_PRE_DELIVERY_QUALITY_GATE.md) |
| Why token budget matters | [M005](../spec/canonical/core/mandates/M005_TOKEN_ECONOMY.md), [execution-budget.md](../spec/canonical/core/economy/execution-budget.md) |
| How to deploy safely | [observability.md](../spec/canonical/specifications/observability.md), [compliance.md](../spec/canonical/specifications/compliance.md) |

---

**Authority:** CORE — Source of Truth
**Scope:** All projects, all agents, all sessions
**Mutability:** Immutable (changes require RFC process)
**Last Updated:** See `.providence/metadata.json`
