# Mandate: Token Economy Enforcement

**Type:** HARD MANDATE
**ID:** M005
**Category:** Economy / Resource Governance

---

## 🎯 Goal

Ensure every agent respects token budget zones and circuit-breaker thresholds to prevent
context overflow, degraded output, and undetected budget breaches.

---

## 📜 Requirement

Agents MUST enforce the following budget zones on every task:

| Zone    | Range          | Required Action                                          |
|---------|----------------|----------------------------------------------------------|
| GREEN   | < 70%          | Proceed normally.                                        |
| YELLOW  | 70–90%         | Apply compression before loading additional context. No warn event. |
| RED     | > 90%          | Emit `economy.budget.warn`. MUST apply compression. Skip non-essential context loads. |
| BREACH  | ≥ 100%         | Emit `economy.budget.breach`. BLOCK all further context loading. Escalate to human checkpoint on PATH A. |

### Circuit Breaker Ceilings

- **Retry ceiling per task:** ≤ 3 retries. Emit `economy.retry.cap.reached` on breach.
- **Reflection ceiling per decision:** ≤ 2 reflections.

### Telemetry Events (normative)

| Event                        | Trigger condition                         |
|------------------------------|-------------------------------------------|
| `economy.budget.warn`        | `budget_utilization_pct > 90`             |
| `economy.budget.breach`      | `budget_utilization_pct >= 100`           |
| `economy.retry.cap.reached`  | retry count exceeds ceiling               |
| `economy.compression.skip`   | compression unavailable in YELLOW/RED     |

---

## 🛠️ Implementation

- **Runtime module:** `packages/core/providence_runtime/src/providence_runtime/telemetry.py`
  - `TelemetrySink._maybe_emit_zone_event()` — zone detection and event emission
  - `_ZONE_YELLOW_PCT = 70.0`, `_ZONE_RED_PCT = 90.0`, `_ZONE_BREACH_PCT = 100.0`
- **Circuit breaker:** `packages/core/providence_runtime/src/providence_runtime/context.py`
  - `RetryBudget` — retry ceiling enforcement
- **Entropy scoring:** `packages/core/providence_runtime/src/providence_runtime/entropy.py`
  - `EntropyScore.compute(retry_count, reflection_count, budget_utilization_pct)`

---

## ⚖️ Rationale

Without enforced budget zones, agents silently overflow the context window, producing
incomplete or hallucinated responses. Zone-based enforcement gives a graduated response:
compression at YELLOW, explicit warning at RED, hard block at BREACH.

---

## ✅ Validation

- [ ] `economy.budget.warn` fires only when `budget_utilization_pct > 90` (not at 70%).
- [ ] `economy.budget.breach` fires when `budget_utilization_pct >= 100`.
- [ ] No further context loads occur after BREACH.
- [ ] Retry count never exceeds 3 without `economy.retry.cap.reached` being emitted.

---

## Skill-Oriented Reinforcement (Normative)

- [ ] Every skill execution MUST declare and enforce a budget policy (token budget, timeout, retry cap).
- [ ] Escalation policy MUST be evaluated when retry or budget limits are reached.
- [ ] `strict` enforcement mode MUST block continuation after critical budget/policy breach.

---

## Enforcement Steps

- Verify current token budget zone before loading any additional context (GREEN < 70%, YELLOW 70–90%, RED > 90%, BREACH ≥ 100%)
- Apply compression before loading context when in YELLOW or RED zone
- Emit `economy.budget.warn` when `budget_utilization_pct > 90`
- Emit `economy.budget.breach` and block all further context loading when `budget_utilization_pct >= 100`
- Confirm retry count never exceeds 3 per task; emit `economy.retry.cap.reached` if ceiling is hit
- Confirm reflection count never exceeds 2 per decision

---

## References

- Normative KPI contract: [`economy/metrics.md`](../economy/metrics.md)
- Zone table: [`economy/execution-budget.md`](../economy/execution-budget.md)
- Efficiency policy: [`economy/efficiency-policy.md`](../economy/efficiency-policy.md)
- Runtime telemetry tests: `packages/core/providence_runtime/tests/test_economy.py`
