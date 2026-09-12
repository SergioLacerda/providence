# SDD Runtime — Decision Log

**Module:** `packages/core/providence_runtime`
**Purpose:** Governance context loading, token economy, policy validation
**Owner:** @SergioLacerda

---

## DEC-2026-001: Context Loading on Demand, Not Preloading (2026-02-01)

**Decision:** Load governance context only when explicitly requested (`providence ask`), not on startup

**Rationale:**
- Startup speed: No I/O blocking, CLI launches instantly
- Efficiency: Only load what you use
- Flexibility: Different contexts for different queries
- Testability: Mock or skip context loading in tests

**Alternatives rejected:**
- Preload all on startup: Slow, wasteful for single queries
- Async preload: Complex, threading issues

**Consequence:** First query slightly slower (cold load), subsequent queries cached

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** ContextLoader in context.py

---

## DEC-2026-002: Budget-Aware Context Loading (2026-03-01)

**Decision:** Each context load checks token budget, raises BudgetBreachError if ≥100%

**Rationale:**
- Token economy (Phase 3): Cap AI usage per session
- Safety: Prevent runaway token consumption
- Explicit: User must acknowledge breach, not silent failure
- Recoverable: Can reset budget, don't crash process

**Consequence:** Callers MUST catch BudgetBreachError and escalate to human

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** BudgetBreachError, ContextRequest.budget_utilization_pct

---

## DEC-2026-003: ContextResult Returns Metadata, Not Just Strings (2026-03-15)

**Decision:** load_result() returns ContextResult (items, source, matched, truncated, bytes_loaded), not just list[str]

**Rationale:**
- Observability: Know if result from artifact or fallback
- Metrics: bytes_loaded for token accounting
- Debugging: matched count tells if query was specific
- truncated flag: User knows results are incomplete

**Backward compat:** load() method still returns list[str] (wraps load_result())

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-004: Query Matching: Exact > Partial (2026-04-01)

**Decision:** When matching queries: (1) exact ID match, (2) partial match in ID/title/description

**Rationale:**
- User expects `providence ask M001` to find M001, not M0010, M0011, ...
- Exact ID first (fast path)
- Partial matches only if no exact
- Case-insensitive (user convenience)

**Example:**
```
providence ask "M001" → exact match, return [M001]
providence ask "mandate" → partial, return all items with "mandate" in description
providence ask "architecture" → partial, return all items with "architecture" label
```

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** ContextLoader._match_items()

---

## DEC-2026-005: Optional Item Type Filtering (2026-04-10)

**Decision:** ContextRequest supports optional item_types filter (e.g., ["MANDATE", "GUIDELINE"])

**Rationale:**
- Some queries only want mandates (M000), not guidelines (G000)
- Optional: If empty, returns all types
- Case-insensitive
- Reduces false positives in results

**Example:**
```python
req = ContextRequest(query="test", item_types=["MANDATE"])
# Returns only items where item_type == "MANDATE"

req = ContextRequest(query="test", item_types=[])
# Returns all types (no filter)
```

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-006: Fallback Response When Artifact Missing (2026-04-20)

**Decision:** If no artifact provided, return deterministic fallback stub (not error)

**Rationale:**
- Graceful degradation: CLI doesn't crash if artifact missing
- Testing: Easy to mock, no file I/O
- Deterministic: Same query always returns same stub
- User-friendly: Better than "file not found"

**Example:**
```python
req = ContextRequest(query="test", artifact=None)
result = loader.load_result(req)
# Returns: items=['context:test'], source='fallback', matched=1

req = ContextRequest(query="", artifact=None)
result = loader.load_result(req)
# Returns: items=[], source='fallback', matched=0 (empty query)
```

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-007: LRU Cache with TTL (5 min) (2026-05-01)

**Decision:** Cache context query results in-memory, max 128 entries, 5-minute TTL

**Rationale:**
- Repeated queries: 95% hit rate in typical usage
- TTL: Stale data expires automatically (5 min balance)
- LRU: Evict least-recently-used when cache full
- 128 entries: Enough for typical session, minimal memory
- No external deps: Custom implementation

**Consequence:** Same query within 5min returns cached result (<1μs latency)

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** packages/core/providence_runtime/src/providence_runtime/cache.py

**Future:** Evaluate Redis for multi-instance deployments (Phase 5.5)

---

## DEC-2026-008: Cache Key = SHA256(artifact_id, query, max_items, item_types) (2026-05-05)

**Decision:** Cache key is deterministic hash, not incremental counter

**Rationale:**
- Stable: Key doesn't change between runs (reproducible)
- Safe: Unlikely collisions (SHA256 is 256-bit)
- Debuggable: Can reproduce key from parameters
- Serializable: Can store/dump cache for analysis

**Alternative rejected:** Simple counter (0, 1, 2, ...) — not reproducible

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-009: Cache Hit/Miss Statistics (2026-05-08)

**Decision:** Track cache stats: hits, misses, hit_rate_pct, entries, max_size

**Rationale:**
- Observability: Know if caching working
- Optimization: Data for tuning cache size/TTL
- Debugging: Diagnose cache poisoning
- User transparency: `sdd cache stats` shows efficiency

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** ContextCache.stats()

---

## DEC-2026-010: Policy Validator (Future Placeholder) (2026-05-11)

**Decision:** reserved for policy validation (when implemented in Phase 5.4/5.5)

**Rationale:**
- Validate governance policies against runtime events
- Check mandate compliance
- Enforce budget constraints
- Future expansion: threat modeling, incident response

**Status:** PENDING (design phase)
**Owner:** @SergioLacerda

---

## DEC-2026-011: Telemetry Integration (Phase 3 Token Economy) (2026-03-15)

**Decision:** Runtime emits telemetry events for: context loads, budget updates, cache hits/misses

**Rationale:**
- Observability: Monitor runtime behavior
- Token accounting: Track resource consumption
- Debugging: Replay sessions to reproduce issues
- Analytics: Understand user patterns

**Events emitted:**
- `runtime.context_load` (query, matched_count, bytes_loaded, source)
- `runtime.budget_update` (delta_tokens, utilization_pct)
- `runtime.cache_hit` (query, cache_age_ms)

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** Phase 3 Token Economy, packages/core/providence_telemetry

---

## DEC-2026-012: Skills Execution Authority in Runtime (2026-05-13)

**Decision:** Capability execution is owned by `providence_runtime` (`SkillEngine`), not by CLI command modules.

**Rationale:**
- Enforces one canonical policy/budget/escalation path.
- Reduces interface-layer coupling and duplicated behavior across tools.
- Keeps telemetry/audit consistent for all skill executions.

**Consequence:** CLI becomes adapter-only for skills operations.

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** `packages/core/providence_runtime/src/providence_runtime/skills.py`
