# 🧠 CORE — Immutable Governance Kernel

## 🎯 Purpose

Define the non-negotiable behavior of the SDD Agent System.

This layer is ALWAYS loaded at runtime.

---

## 🔒 Invariants

- Cannot be modified by agents
- Cannot be bypassed during execution
- Always compiled into `.providence/compiled/`
- Must be loaded before ANY task

---

## 🧬 Structure

> [!IMPORTANT]
> The source of truth for mandates and guidelines is located in the `meta/` directory.

- **mandates/**   → required behaviors (execution protocol)
- **meta/mandate.spec** → [PRIMARY SOURCE] Mandate definitions (M001-M003)
- **meta/guidelines.dsl** → [PRIMARY SOURCE] Customization guidelines
- **policies/**   → governance constraints
- **cognition/**  → decision strategy (routing, context loading)
- **economy/**    → token resource governance (budgets, metrics, efficiency policy)
- **telemetry/**  → runtime observability & audit (OTEL bridge, events)
- **rules/**      → code + architecture constraints
- **generated/**  → execution contract (agent protocol)

---

## ⚙️ Runtime Binding

Compiled into:

.providence/compiled/

Includes:

- structured JSON (not markdown)
- indexed access
- fingerprint validation

---

## 🔁 Mandatory Load Sequence

1. Detect `.spec.config`
2. Load `.providence/compiled/` indices
3. Validate fingerprint
4. Activate governance mode

---

## 🚨 Failure Mode

If CORE is not loaded:

→ System enters DEGRADED MODE
→ Responses are NOT governance-compliant

---

## 🔐 Enforcement Rule

> No reasoning without CORE.
