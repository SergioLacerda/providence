> Layer: spec/canonical - immutable governance definition

> Generated mirror notice: this page is a publication mirror for runtime agent
> protocol material. Edit the classified source under `docs/`; regenerate
> `.providence/` runtime outputs instead of editing generated runtime files directly.

# 🧠 AGENT ENTRYPOINT --- SDD Execution Kernel

## 🎯 Purpose

Provide a SINGLE deterministic execution entrypoint.

## 🔒 CORE PRINCIPLE

No execution without governance awareness.

## 🔁 EXECUTION PIPELINE

1. ENVIRONMENT DETECTION

- Check `.spec.config`
- Check `.providence/source/` If missing → DEGRADED MODE

1. HANDSHAKE

- Execute HANDSHAKE.md

1. LOAD CORE

- mandates/index.md
- policies/index.md
- cognition/index.md
- rules/index.md
- economy/index.md ← load when: context > 60% budget, multi-agent session, or CI execution

1. TASK CLASSIFICATION

- TASK_CLASSIFICATION.md

1. CONTEXT LOADING

- strategy.md
- path-routing.md
- context-budget.md

1. DECISION

- CONTEXT_SELECTION.md
- EXECUTION_DECISION.md

1. ANTI-PATTERN CHECK

- Validate no violations

1. EXECUTION PRIORITY Mandates > Policies > Rules

2. VALIDATION

- Validate mandates, policies, rules
- **Apply P004 Pre-Delivery Quality Gate** →
    `docs/spec/canonical/core/policies/P004_PRE_DELIVERY_QUALITY_GATE.md`
    1. Detect available quality tooling (Makefile, pyproject.toml, etc.)
    2. Classify project: EQUIPPED / PARTIAL / LEGACY
    3. Run all mandatory tools — block delivery if any fail
    4. Include `[PDQG STATUS]` block in handoff message

1. OUTPUT

[SDD STATUS] Governance: ACTIVE | DEGRADED Context: LOADED Mode:
COMPLIANT | HEURISTIC Path: A | B | C | D

## ⚠️ HEURISTIC MODE

Use HEURISTIC_EXECUTION.md

## 🔐 FINAL RULE

Agent MUST NOT execute without context, mandates and policies.
