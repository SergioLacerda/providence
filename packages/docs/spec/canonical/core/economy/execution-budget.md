# 🔋 Execution Budget — Hard Limits & Circuit Breakers

## 🎯 Purpose

Enforce token/context ceilings per PATH and define the circuit-breaker behavior when budgets are exceeded.

---

## 🔒 Core Principle

> More context does not improve results — it degrades them.
> Budget enforcement is not optional.

---

## 📊 Budget Ceilings per PATH

Context KB targets sourced from `cognition/context-loading/context-budget.md`.
Token ceilings derived at **280 tokens/KB** (mixed markdown+code, ~3.7 chars/token).
System instructions overhead: ~3,000 tokens. Models: claude-sonnet-4-6 / claude-opus-4-6 (200K context, shared tokenizer).

| PATH | Scenario | Context Budget | Input Token Ceiling | Output Budget | Total Token Ceiling |
|------|----------|---------------|---------------------|---------------|---------------------|
| A | Bug Fix | 40 KB | 12,000 | 2,000 | 17,000 |
| B | Simple Feature | 45 KB | 14,000 | 4,000 | 21,000 |
| C | Complex Feature | 85 KB | 24,000 | 8,000 | 35,000 |
| D | Multi-thread | 35 KB/thread | 10,000/thread | 2,000/thread | 15,000/thread |

**Conversion formula:**
`input_token_ceiling = context_kb × 280`
`total_token_ceiling = input_token_ceiling + system_tokens(3000) + output_budget`

> **Re-baseline when:** model is changed, tokenizer is updated, or measured `tokens_input` exceeds ceiling by >15% on 3+ consecutive tasks.
> Measured values from `economy.budget.breach` / `economy.budget.warn` events in the compliance events log are authoritative over estimates. (Projects maintain this log in `.ai` during execution.)

---

## 🚦 Budget Utilization Zones

| Zone | Utilization | Required Action |
|------|-------------|-----------------|
| GREEN | < 70% | Proceed normally |
| YELLOW | 70–90% | Apply compression if available |
| RED | > 90% | Emit `economy.budget.warn`; MUST apply compression; skip non-essential context loads |
| BREACH | ≥ 100% | Emit `economy.budget.breach`; BLOCK all further context loading |

---

## ⚡ Circuit Breaker Rules

1. Agent MUST emit `economy.budget.warn` when `budget_utilization_pct > 90`
2. Agent MUST emit `economy.budget.breach` when `budget_utilization_pct >= 100`
3. Agent MUST NOT load additional context once BREACH is reached
4. Agent MUST record `budget_utilization_pct` in every session-end event
5. Agent MUST abort non-essential context loads and proceed with available context at BREACH
6. Agent MUST escalate to human checkpoint if BREACH is reached on PATH A

---

## 🔒 Programmatic Enforcement

Rule 3 ("MUST NOT load additional context once BREACH is reached") is enforced as a Python exception:

- `ContextLoader.load_result()` raises `BudgetBreachError` when `budget_utilization_pct >= 100`
- The exception carries `utilization_pct` and optional `path_id` for logging/escalation
- **Caller responsibility:** catch this exception and escalate to a human checkpoint
- No further calls to `ContextLoader.load_result()` are permitted in the session
- Implementation: `packages/core/providence_runtime/src/providence_runtime/context.py:BudgetBreachError`

---

## 🏷️ `path_id` Namespace — Two Separate Concepts

`path_id` appears in two unrelated places in this codebase — do not conflate them:

- **Canonical PATH A–F** (this document + `cognition/context-loading/path-routing.md`)
  — a task-complexity classification for the *agent's current working session*
  (bug fix, feature, complex feature, multi-thread, incident, structural cleanup).
  Carried via the `SDD_PATH_ID` environment variable and consulted by
  `_PATH_BUDGET_BYTES` for budget-ceiling lookups. `BudgetBreachError.path_id`
  (see Programmatic Enforcement above) reflects this taxonomy only when a caller
  explicitly passes it.
- **Tool-internal routing labels** — some CLI commands emit their own `path_id`-shaped
  telemetry label for unrelated per-call routing decisions (e.g. `providence ask` uses
  `PATH_A`/`PATH_B` to record whether a query triggered heavy `sdd-organize` intake).
  These labels answer a different question than the canonical PATH classification
  above and must never be mapped onto it — doing so would misclassify the agent's
  task budget based on an unrelated signal.

**Current state:** as of this writing, no component in this codebase sets
`SDD_PATH_ID` in production — the canonical PATH A–F circuit breaker described above
has no live producer feeding it a real classification. `BudgetBreachError.path_id`
is `None`/unset unless a caller supplies it explicitly.

---

## 💾 Context Cache Interaction

The `ContextCache` (LRU, 128 entries, 5-min TTL) has important economy implications:

- Cache hits return pre-computed `context_bytes_loaded` values from a previous call
- Cache hits do NOT re-trigger the YELLOW zone compression path
- If a cached result was computed when budget utilization was GREEN, it will be returned as-is even if current utilization is YELLOW
- **Policy:** Cache statistics and budget utilization are independent; always check current utilization when budget concerns exist
- Implementation: `packages/core/providence_runtime/src/providence_runtime/cache.py:ContextCache`

---

## 🔧 Compression Mechanism: ProviderRegistry

The `ContextLoader` orchestrates compression via a pluggable `ProviderRegistry`:

- Providers are attempted in configurable priority order
- Default priority: `HttpProvider` → `AstProvider` → `TfidfProvider` → `LocalIntelligenceProvider`
- Each provider implements the `IntelligenceProvider` protocol: `compress_context(bundle) → CompressedContext`
- The first available provider that returns a result is used
- At YELLOW zone (70–90%), `ContextLoader` targets bringing utilization down to 70% after compression
- Implementation: `packages/core/providence_runtime/src/providence_runtime/context.py:ContextLoader.__init__` and `load_result()`

---

## 📐 The 30/70 Rule

| Component | Target % | Purpose |
|-----------|----------|---------|
| System Instructions | 5% | Core behavior and governance |
| Context (Docs + Code) | ≤ 65% | The "What" and "Where" |
| Reasoning Space | ≥ 30% | Empty — required for output quality |

> **WARNING**: If Docs + Code > 70%, model reasoning degrades ("Lost in the Middle" effect).

---

## 🚨 Anti-Patterns

- Ignoring the utilization zone and loading context freely
- Loading additional artifacts after BREACH signal
- Reporting `budget_utilization_pct` without actual measurement (estimated ≠ measured)
- Treating YELLOW as GREEN and skipping compression
- Applying compression after BREACH (too late — prevent, don't react)

---

## 🔗 Normative References

- `→ cognition/context-loading/context-budget.md` — budget KB targets (authoritative source)
- `→ economy/metrics.md` — `budget_utilization_pct` field definition
- `→ economy/efficiency-policy.md` — compression obligations triggered at YELLOW/RED
