# 📏 Economy Metrics — Canonical KPI Definitions

## 🎯 Purpose

Define the normative field names, types, and measurement points for token economy observability.
Field names in this document are **authoritative** — implementation MUST match exactly.

---

## 🔒 Contract Rule

> Any telemetry field that measures token consumption, context load, or execution budget
> MUST use the field names defined in this document.

---

## 📊 RuntimeEvent Economy Fields

Added to `RuntimeEvent` dataclass in `packages/core/providence_runtime/src/providence_runtime/telemetry.py`.

| Field | Type | Description |
|-------|------|-------------|
| `tokens_input` | `int \| None` | LLM input tokens consumed this event |
| `tokens_output` | `int \| None` | LLM output tokens generated this event |
| `tokens_total` | `int \| None` | Sum of input + output (convenience field) |
| `context_bytes_loaded` | `int \| None` | Total bytes loaded into context window |
| `context_budget_bytes` | `int \| None` | Budget ceiling for this PATH in bytes |
| `budget_utilization_pct` | `float \| None` | `context_bytes_loaded / context_budget_bytes * 100` |
| `compression_ratio` | `float \| None` | `compressed_bytes / original_bytes` (1.0 = no compression; 0.6 = 40% reduction) |
| `retry_count` | `int \| None` | Number of retries within this task unit |
| `reflection_count` | `int \| None` | Number of self-reflection cycles within this decision point |
| `path_id` | `str` | Active PATH: `"A"` \| `"B"` \| `"C"` \| `"D"` |

---

## ⚡ Economy Event Types

| Event Type | Trigger Condition | Status |
|------------|-------------------|--------|
| `economy.budget.warn` | `budget_utilization_pct > 90` | warn |
| `economy.budget.breach` | `budget_utilization_pct >= 100` | warn |
| `economy.compression.skip` | In YELLOW zone but compression not applied | info |
| `economy.retry.cap.reached` | `retry_count >= ceiling` (see `efficiency-policy.md`) | warn |

> `economy.budget.breach` is a **mandatory event** — always emitted regardless of logging mode.

---

## 📐 KPI Thresholds

These are informational targets, not hard limits (hard limits are in `execution-budget.md`).

| KPI | Target | Violation Signal |
|-----|--------|-----------------|
| `compression_ratio` | ≤ 0.6 | Compression underperforming |
| `budget_utilization_pct` | ≤ 85% | Leave headroom for output |
| `retry_count` per event | ≤ 3 | See `efficiency-policy.md` for ceiling |
| `reflection_count` per decision | ≤ 2 | See `efficiency-policy.md` for ceiling |
| `tokens_total` PATH A | ≤ 17,000 | Bug Fix: 12K input + 3K system + 2K output |
| `tokens_total` PATH B | ≤ 21,000 | Simple Feature: 14K input + 3K system + 4K output |
| `tokens_total` PATH C | ≤ 35,000 | Complex Feature: 24K input + 3K system + 8K output |
| `tokens_total` PATH D | ≤ 15,000/thread | Multi-thread: 10K input + 3K system + 2K output per thread |

---

## ⏱ Measurement Points

Each field MUST be populated at the following points in the execution lifecycle:

| Field | When to Populate |
|-------|-----------------|
| `tokens_input` | At LLM call return |
| `tokens_output` | At LLM call return |
| `tokens_total` | Computed after LLM call return |
| `context_bytes_loaded` | At context load completion |
| `context_budget_bytes` | At PATH selection (constant for PATH) |
| `budget_utilization_pct` | Computed after each context load |
| `compression_ratio` | At compression operation completion |
| `retry_count` | Incremented per retry; recorded at session end |
| `reflection_count` | Incremented per reflection; recorded at session end |
| `path_id` | At task classification (TASK_CLASSIFICATION step) |

---

## 🔭 OTEL Attribute Mapping

All economy fields are exported under the `sdd.economy.*` namespace.

| RuntimeEvent Field | OTEL Key |
|--------------------|----------|
| `tokens_input` | `sdd.economy.tokens_input` |
| `tokens_output` | `sdd.economy.tokens_output` |
| `tokens_total` | `sdd.economy.tokens_total` |
| `context_bytes_loaded` | `sdd.economy.context_bytes_loaded` |
| `context_budget_bytes` | `sdd.economy.context_budget_bytes` |
| `budget_utilization_pct` | `sdd.economy.budget_utilization_pct` |
| `compression_ratio` | `sdd.economy.compression_ratio` |
| `retry_count` | `sdd.economy.retry_count` |
| `reflection_count` | `sdd.economy.reflection_count` |
| `path_id` | `sdd.economy.path_id` |

> All economy attributes are **optional** in OTEL export — only emitted when non-None/non-empty.

---

## 📝 Notes on `compression_ratio`

**Convention:** `compression_ratio = compressed_bytes / original_bytes`

- Value 1.0 → no compression occurred
- Value < 1.0 → compression successful (e.g., 0.5 = 50% size reduction)
- All built-in providers (`TfidfProvider`, `AstProvider`, `LocalIntelligenceProvider`) follow this convention
- External HTTP providers (via `SDD_INTELLIGENCE_URL`) MUST comply

**Provider tracking:** The intelligence provider that performed compression is captured in
`CompressedContext.provider` but is NOT surfaced in `RuntimeEvent`. It is available in debug logs
from `ContextLoader.load_result()`.

---

## 🔗 References

- `→ economy/execution-budget.md` — budget ceilings and breach thresholds
- `→ economy/efficiency-policy.md` — retry/reflection ceiling definitions
- `→ packages/core/providence_runtime/src/providence_runtime/telemetry.py` — RuntimeEvent implementation
- `→ packages/core/providence_runtime/src/providence_runtime/llm.py` — LLM token capture (populates `tokens_*` fields)
- `→ packages/core/providence_runtime/src/providence_runtime/otel.py` — OtelAttributes implementation
