# Anti-Pattern: Overloading Context

## Definition

Loading more documentation, code, or examples into context than needed for the current task, consuming tokens and reasoning space beyond the PATH budget allocation.

---

## Symptoms

- Context window exceeds PATH budget (see [execution-budget.md](../../economy/execution-budget.md))
- Agent loads entire CANONICAL documentation for a simple task
- All guides loaded even when only one guide is relevant
- Multiple related files loaded when a summary would suffice
- Token utilization enters YELLOW (71–90%) or RED (91–99%) zone unnecessarily

---

## Root Cause

- No task classification before loading context
- "Load everything to be safe" rather than minimal-sufficient strategy
- No understanding of PATH budget constraints
- Missing context selection decision (see [CONTEXT_SELECTION.md](../decision-models/CONTEXT_SELECTION.md))

---

## Impact

- ❌ Wasted tokens that compress reasoning space (violates [execution-budget.md](../../economy/execution-budget.md))
- ❌ Reduced reasoning quality due to context bloat
- ❌ Potential breach of token ceiling (violates M005 Token Economy)
- ❌ May trigger unwanted compression or circuit breaker

---

## Prevention

1. **Always classify task first** → Select PATH (A–F) per [TASK_CLASSIFICATION.md](../decision-models/TASK_CLASSIFICATION.md)
2. **Check budget before loading** → Know your context ceiling per PATH
3. **Use [CONTEXT_SELECTION.md](../decision-models/CONTEXT_SELECTION.md)** → Load only what applies to YOUR task
4. **Verify against [search-keywords.md](../../../../../indices/search-keywords.md)** → Use indices for targeted lookups
5. **Reserve 30% context for reasoning** → Never exceed 70% on docs (see 30/70 Rule in [execution-budget.md](../../economy/execution-budget.md))

---

## Cure

1. **Immediate:** Review what's loaded; remove non-essential files
2. **Re-classify:** Run TASK_CLASSIFICATION → confirm PATH is correct
3. **Re-select context:** Use CONTEXT_SELECTION decision model → load only what applies
4. **Measure:** Check context % utilization via `providence runtime status`
5. **If still over:** Trigger compression (see [efficiency-policy.md](../../economy/efficiency-policy.md))

---

## Related

- [context-budget.md](../context-loading/context-budget.md) — Budget targets per PATH
- [execution-budget.md](../../economy/execution-budget.md) — Hard ceilings and zones
- [CONTEXT_SELECTION.md](../decision-models/CONTEXT_SELECTION.md) — How to choose what to load
- [efficiency-policy.md](../../economy/efficiency-policy.md) — Compression requirements
