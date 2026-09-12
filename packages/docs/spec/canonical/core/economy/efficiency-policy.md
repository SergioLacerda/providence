# ⚙️ Efficiency Policy — Compression & Retry Governance

## 🎯 Purpose

Define mandatory efficiency behaviors: when compression MUST be applied, ceiling on retries and reflections, and escalation on breach.

---

## 🔒 Core Principle

> Deterministic tools resolve syntactic problems.
> Budget governance resolves cognitive entropy.
> Neither replaces the other.

---

## 📦 Compression Obligations

| Condition | Required Action |
|-----------|-----------------|
| `budget_utilization_pct >= 70%` | MUST attempt compression before loading more context |
| In YELLOW zone but compression not applied | Emit `economy.compression.skip` (`status=info`) |
| Post-compression `compression_ratio > 0.8` | Compression was ineffective; log and proceed without retrying |
| `budget_utilization_pct > 90%` after compression | Escalate to RED zone; skip non-essential loads |

### Compression Implementation: ProviderRegistry

The `ContextLoader` uses a `ProviderRegistry` with a cascading provider chain:

| Priority | Provider | Strategy | When Available |
|----------|----------|----------|-----------------|
| 1 | `HttpProvider` | Delegates to external service at `SDD_INTELLIGENCE_URL` | Only when env var is set |
| 2 | `AstProvider` | Python AST analysis + deduplication (for code) | Always (graceful degradation) |
| 3 | `TfidfProvider` | TF-IDF cosine similarity ranking (pure Python) | Always (no dependencies) |
| 4 | `LocalIntelligenceProvider` | Dedup + budget-fit truncation (final fallback) | Always (built-in) |

**Degradation contract:** Compression always succeeds. If all external providers fail (network, misconfiguration),
`LocalIntelligenceProvider` is guaranteed to return a response. Providers never raise exceptions — failures are
logged and the next provider is tried automatically.

**Target at YELLOW zone:** When utilization is 70–90%, `ContextLoader` computes a target budget
(`original_bytes × 70 / utilization_pct`) and aims to fit within it, bringing utilization down to 70%.

**Implementation:** `packages/core/providence_runtime/src/providence_runtime/context.py:ContextLoader.load_result()`
and `packages/core/providence_runtime/src/providence_runtime/providers/`

---

## 🔁 Retry Ceilings

| PATH | Retry Ceiling | On Breach |
|------|---------------|-----------|
| A | 2 | Abort task; require human checkpoint |
| B | 3 | Emit `economy.retry.cap.reached`; continue with warning |
| C | 3 | Emit `economy.retry.cap.reached`; continue with warning |
| D | 2 per thread | Abort thread; escalate |

---

## 🪞 Reflection Ceilings

| PATH | Reflection Ceiling | On Breach |
|------|--------------------|-----------|
| A | 1 | Abort reflection; commit to current decision |
| B | 2 | Emit `economy.retry.cap.reached`; proceed |
| C | 2 | Emit `economy.retry.cap.reached`; proceed |
| D | 1 per thread | Abort reflection; commit |

> **Rationale**: More reflection ≠ more quality. Beyond ceiling, reflection adds entropy, not convergence.

---

## ⚡ Hard Rules

1. Agent MUST apply compression when `budget_utilization_pct > 70%` and compression is available
2. Agent MUST NOT exceed `retry_count` ceiling for the active PATH
3. Agent MUST NOT exceed `reflection_count` ceiling per decision point
4. Agent MUST record `retry_count` and `reflection_count` in every session-end event
5. Agent MUST emit `economy.retry.cap.reached` before any retry that would breach the ceiling
6. Agent MUST escalate to human checkpoint when PATH A retry ceiling is reached

---

## 🚨 Anti-Patterns

- Retrying without incrementing `retry_count`
- Applying compression only after BREACH (prevent, do not react)
- Treating reflection loops as progress when `reflection_count >= ceiling`
- Running full test suites to resolve a PATH A task (test scope must match PATH scope)
- Expanding task scope during reflection ("maybe the architecture needs to change")

---

## 📐 Cognitive Entropy Indicators

Escalate to human checkpoint when ANY of the following occur:

| Signal | Threshold |
|--------|-----------|
| `retry_count` at ceiling | PATH-dependent (see table above) |
| `budget_utilization_pct` at BREACH | ≥ 100% |
| Consecutive `economy.compression.skip` events | ≥ 2 |
| Task scope expanded during reflection | any occurrence |

---

## 🔗 References

- `→ cognition/context-loading/strategy.md` — compression techniques
- `→ economy/execution-budget.md` — BREACH zone definition
- `→ economy/metrics.md` — `retry_count`, `reflection_count`, `compression_ratio` field names
