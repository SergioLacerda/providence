# 💰 ECONOMY — Token Resource Governance

## 🎯 Purpose

Govern token consumption and context efficiency as a first-class compliance concern.

---

## 🔒 Invariant

Economy is:

- immutable
- enforcement-oriented (not a decision strategy)
- always loaded alongside CORE

---

## 📊 Scope

| This section governs | Deferred to |
|----------------------|-------------|
| Hard token/context ceilings per PATH | `cognition/context-loading/context-budget.md` |
| Budget utilization zones + circuit breakers | ← here |
| Canonical KPI field names and types | ← here (`metrics.md`) |
| Compression and retry enforcement rules | ← here (`efficiency-policy.md`) |
| Compression techniques | `cognition/context-loading/strategy.md` |
| PATH selection rules | `cognition/context-loading/path-routing.md` |
| Context cache management | `mandates/M003_CONTEXT_AWARENESS.md` |

---

## 📂 Modules

| File | Governs |
|------|---------|
| `execution-budget.md` | Hard limits, GREEN/YELLOW/RED/BREACH zones, circuit-breaker rules |
| `metrics.md` | Canonical KPI definitions, RuntimeEvent fields, OTEL attribute mapping |
| `efficiency-policy.md` | Compression obligations, retry/reflection ceilings, anti-patterns |

---

## 🔧 Implementation Modules

| Module | Responsibility |
|--------|-----------------|
| `llm.py` | LLM token capture: `LLMTokenCapture` protocol, `SimulatedTokenCapture`, env-var injection |
| `context.py` | Context loading with budget zone enforcement and YELLOW zone compression trigger |
| `cache.py` | In-memory LRU context cache; cache hits bypass compression re-check |
| `providers/` | Intelligence provider registry: TF-IDF, AST, HTTP compression providers |
| `intelligence.py` | IntelligenceProvider protocol, ProviderRegistry, provider data types |
| `telemetry.py` | RuntimeEvent schema, zone event emission (`economy.budget.*`, `economy.compression.*`) |

---

## 🔁 Mandatory Load Condition

Load `economy/index.md` when:

- task context exceeds 60% of PATH budget
- any `economy.*` event must be emitted
- token-sensitive execution is required (CI, multi-agent, long sessions)

---

## 🔗 Cross-References

**Canonical governance sources:**

- `→ cognition/context-loading/context-budget.md` — budget KB targets (do not redefine here)
- `→ cognition/context-loading/strategy.md` — compression techniques (do not redefine here)
- `→ mandates/M003_CONTEXT_AWARENESS.md` — context cache mandate

**Implementation sources (authoritative for field names, thresholds):**

- `→ packages/core/providence_runtime/src/providence_runtime/telemetry.py` — RuntimeEvent schema, zone event emission
- `→ packages/core/providence_runtime/src/providence_runtime/context.py` — ContextLoader, BudgetBreachError exception
- `→ packages/core/providence_runtime/src/providence_runtime/llm.py` — LLM token capture protocol and implementation
- `→ packages/core/providence_runtime/src/providence_runtime/cache.py` — ContextCache LRU implementation
- `→ packages/core/providence_runtime/src/providence_runtime/providers/` — Intelligence provider implementations

---

## 🚨 Failure Mode

If economy governance is ignored:

→ Context inflation goes undetected
→ Budget breaches are silent
→ Token costs grow without visibility
→ Agent cognitive entropy increases unchecked
