from __future__ import annotations

from typing import Any


def generate_constitution_specialization_tail(config: dict[str, Any]) -> str:
    project = config["PROJECT_NAME"]
    max_concurrent = config.get("MAX_CONCURRENT_ENTITIES", "50+")
    return f"""

Coordination via:
  - Message bus for notifications
  - Database for shared read-only data
  - Thread-safe queues for work distribution

Validation:** Thread isolation tests verify no data races (ThreadSanitizer)
```

**Constraint:** {max_concurrent} campaigns must support {max_concurrent} concurrent threads without deadlock

---

### 6. Explicit Error Handling

**Generic:** Never silent failures

**{project} specialization:**
```
Critical failure modes:
  1. LLM API timeout → log + fallback to cached narrative
  2. Database connection lost → log + graceful degradation
  3. Vector index unavailable → log + use DB search fallback
  4. Campaign corruption detected → log + ALERT team + pause updates

Error budget:
  - LLM errors: acceptable (fallback to cache)
  - Database errors: NOT acceptable (requires rollback)
  - Index errors: acceptable (rebuild from source)

Monitoring:**
  - error_rate_percent < 0.5% (SLO)
  - error_types tracked by middleware
  - on-call alert for any database errors
```

**Constraint:** Zero unhandled exceptions reach users

---

### 7. Immutable Configuration

**Generic:** Configuration changes require code review

**{project} specialization:**
```
Immutable config (cannot change without deployment):
  - MAX_CAMPAIGNS_PER_USER
  - MAX_CONCURRENT_GENERATIONS
  - LLM_MODEL_VERSION
  - VECTOR_INDEX_DIMENSION

Mutable config (can change live):
  - LLM_TEMPERATURE (within bounds)
  - CACHE_TTL_SECONDS (within bounds)
  - RETRY_BACKOFF_MS (within bounds)

How to change immutable:
  1. Edit pyproject.toml
  2. Create PR (code review required)
  3. Merge to main
  4. Deploy (blue-green deployment)
  5. Rollback plan: revert + redeploy
```

**Constraint:** Immutable config validated at startup, non-compliance → EXIT

---

### 8. Observability is Non-Negotiable

**Generic:** Every request traceable, every error loggable

**{project} specialization:**
```
Tracing requirements:
  - Campaign creation: trace all steps
  - Narrative generation: trace LLM call (tokens, latency)
  - Vector search: trace query (embedding, distance, latency)

Metrics required:
  - campaign_generation_latency_ms (p50, p99)
  - llm_api_calls_total (by model)
  - vector_index_update_lag_ms (max lag allowed)
  - error_rate_percent (by error type)

Logging levels:
  - DEBUG: disabled in production
  - INFO: campaign lifecycle events
  - WARNING: rate limiting, retries
  - ERROR: failures that don't stop system
  - CRITICAL: system-wide failures

Validation:** Every endpoint must log on entry/exit with trace ID
```

**Constraint:** Zero unlogged errors in production

---

### 9-15. [Additional Principles]

[Additional principles would follow same pattern...]

---

## 🔗 References

- Generic principles: [CANONICAL/rules/constitution.md](../../CANONICAL/rules/constitution.md)
- Execution rules: [CANONICAL/rules/ia-rules.md](../../CANONICAL/rules/ia-rules.md)
- Architecture spec: [CANONICAL/specifications/architecture.md](../../CANONICAL/specifications/architecture.md)
- {project} config: [SPECIALIZATIONS_CONFIG.md](./SPECIALIZATIONS_CONFIG.md)

---

## ✅ Validation

**Generated:** {config.get("GENERATED_AT")}
**Next update:** Auto-generated when CANONICAL/ changes
**Manual updates:** {project}-specific constraints only (marked with **specialization**)

"""
