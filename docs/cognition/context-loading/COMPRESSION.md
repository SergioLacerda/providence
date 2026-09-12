# 🗜️ Context Compression — Pluggable Provider Architecture

## Purpose

When the agent loads context and approaches the budget ceiling (70–90% utilization, **YELLOW zone**), the system
automatically compresses context via a pluggable provider chain. This document explains:

1. **When compression happens** — YELLOW zone thresholds
2. **How each provider compresses** — strategy per provider
3. **How to plug in custom providers** — extend the system
4. **Compression ratio convention** — interpretation of the `compression_ratio` field

---

## Budget Zone Trigger

Compression is **automatically attempted** when:

```
ContextLoader.load_result(request)
  └── budget_utilization_pct in [70.0, 100.0)?  ← YELLOW zone
        └── ProviderRegistry.compress_context(bundle)
              └── Try providers in order; use first that succeeds
```

If compression achieves `compression_ratio < 1.0`, the compressed result is used. Otherwise, original context is kept
and an `economy.compression.skip` event is emitted (informational, not a warning).

---

## Provider Chain — Priority Order

The `ProviderRegistry` tries providers in **cascading priority order**. The first **available** provider wins.
If that provider fails, the next is tried. The system **always succeeds** because `LocalIntelligenceProvider` is
guaranteed available.

| Priority | Provider | Strategy | When Available |
|----------|----------|----------|----------------|
| 1 | `HttpProvider` | POST JSON to external `SDD_INTELLIGENCE_URL` service | Only if env var set + endpoint healthy |
| 2 | `AstProvider` | Dedup + budget-fit truncation (Python AST analysis) | Always (graceful degradation on non-Python) |
| 3 | `TfidfProvider` | TF-IDF relevance scoring + keep highest-ranked items | Always (pure Python, no deps) |
| 4 | `LocalIntelligenceProvider` | Exact-match dedup + sequential truncation | Always (built-in fallback) |

**Degradation contract:** If all external providers fail, the system falls back to Local. No exceptions are raised.
Failures are logged at debug level; the next provider is tried automatically.

---

## How Each Provider Compresses

### TfidfProvider

**Strategy:** Rank items by relevance to the query using TF-IDF cosine similarity.

**Algorithm:**

1. Tokenize query and each item (lowercase, split on whitespace)
2. Compute cosine similarity between query tokens and item tokens using `Counter`
3. Score items by relevance
4. Greedily select items (highest relevance first) until accumulated bytes ≤ `budget_bytes`
5. Always keep at least 1 item, even if it exceeds budget

**Compression ratio:** `compressed_bytes / original_bytes`

**Example:**

```python
from providence_runtime.providers import TfidfProvider
from providence_runtime.intelligence import ContextBundle

provider = TfidfProvider()
bundle = ContextBundle(
    items=[
        "class DataProcessor: def process(data): ...",  # 300 bytes
        "class Logger: def log(msg): ...",  # 280 bytes
        "class Config: def load(): ...",  # 250 bytes
    ],
    query="data processing algorithm",
    budget_bytes=400,
)
result = provider.compress_context(bundle)
print(f"Compressed: {result.compression_ratio:.2f}")  # e.g., 0.67 → 67% reduction
```

---

### AstProvider

**Strategy:** Parse Python code, identify structurally-equivalent items, deduplicate + truncate.

**Algorithm:**

1. Parse items as Python AST (fails gracefully for non-Python input)
2. Extract **structural signature** from each item (class/function definitions, imports)
3. Remove exact-duplicate items (first occurrence wins)
4. Drop lowest-value items from the end until accumulated bytes ≤ `budget_bytes`

**Available only for Python code.** For non-Python input, gracefully degrades (returns all items, `compression_ratio=1.0`).

**Example:**

```python
from providence_runtime.providers import AstProvider
from providence_runtime.intelligence import ContextBundle

provider = AstProvider()
bundle = ContextBundle(
    items=[
        "def process(x): return x * 2",  # 30 bytes
        "def process(x): return x * 2",  # 30 bytes (duplicate)
        "def transform(y): return y + 1",  # 32 bytes
    ],
    query="function definitions",
    budget_bytes=50,
)
result = provider.compress_context(bundle)
# After dedup + truncate: 2 items (removed duplicate + last item)
print(f"Items: {len(result.items)}")  # 1 or 2, ratio ≤ 1.0
```

---

### LocalIntelligenceProvider

**Strategy:** Keyword matching + exact-match deduplication + budget-fit truncation.

**Always available.** Guaranteed fallback when all other providers fail.

**Algorithm:**

1. Remove exact-duplicate items (first occurrence wins)
2. Maintain original item order (longest items first, to preserve relevance)
3. Greedily select items until accumulated bytes ≤ `budget_bytes`
4. Always keep at least 1 item, even if oversized

**Compression ratio:** `compressed_bytes / original_bytes`

**Example:**

```python
from providence_runtime.intelligence import LocalIntelligenceProvider, ContextBundle

provider = LocalIntelligenceProvider()
bundle = ContextBundle(
    items=["config.py"] * 3 + ["utils.py"],  # 3 duplicates + 1 unique
    query="module context",
    budget_bytes=20,
)
result = provider.compress_context(bundle)
print(f"Items after dedup: {len(result.items)}")  # 2: ["config.py", "utils.py"]
print(f"Ratio: {result.compression_ratio:.2f}")  # < 1.0 (duplicates removed)
```

---

### HttpProvider

**Strategy:** Delegate compression to an external HTTP service.

**When available:** Only when environment variable `SDD_INTELLIGENCE_URL` is set AND the endpoint responds 200.

**API contract:**

```bash
POST {SDD_INTELLIGENCE_URL}/compress
Content-Type: application/json

{
  "items": ["item1", "item2", ...],
  "query": "task description",
  "budget_bytes": 5000
}

Response (200 OK):
{
  "items": ["item1"],
  "original_bytes": 10000,
  "compressed_bytes": 5000,
  "compression_ratio": 0.5,
  "provider": "external-service"
}
```

**Graceful degradation:** Network failure → returns degraded result (no compression, full items returned). Never raises.

---

## compression_ratio Convention

**Definition:** `compression_ratio = compressed_bytes / original_bytes`

| Value | Meaning |
|-------|---------|
| 1.0 | No compression (output = input size) |
| 0.8 | 20% reduction (80% of original size) |
| 0.5 | 50% reduction (half the size) |
| 0.0 | Theoretical: all items removed (impossible; Local always keeps ≥ 1 item) |

**All built-in providers follow this convention.** External HTTP providers MUST comply.

**In code:**

```python
if compressed.compression_ratio < 1.0:
    # Compression was effective
    use(compressed)
else:
    # No effective compression; use original
    use(original)
```

---

## Cache Interaction

The `ContextCache` (LRU, 128 entries, 5-min TTL) returns pre-computed context bytes from previous requests.

**Important:** Cache hits **bypass the YELLOW zone compression check**. If a result was cached when utilization was
GREEN, it will be returned as-is even if current utilization is YELLOW.

**Implication:** Cached `compression_ratio` may reflect stale budget state. Always check current utilization
via `budget_utilization_pct` field when budget concerns arise.

```python
# Example: cache hit with stale utilization
# T=0: load context, budget_util=60% (GREEN), cache hit, ratio=None
# T=5min: load same context, budget_util=75% (YELLOW), cache hit, ratio=None
#         → compression was not re-attempted even though now in YELLOW
```

---

## Extension Point — Custom Providers

Implement the `IntelligenceProvider` Protocol to create a custom provider:

```python
from providence_runtime.intelligence import (
    IntelligenceProvider,
    TaskContext,
    AnalysisResult,
    ContextBundle,
    CompressedContext,
    BudgetEstimate,
)


class MyCustomProvider:
    """Example custom compression provider."""

    @property
    def name(self) -> str:
        """Stable identifier echoed in result fields."""
        return "my-custom-provider"

    @property
    def available(self) -> bool:
        """True if this provider can service requests right now."""
        # e.g., check API key, network, configuration
        return os.environ.get("MY_PROVIDER_API_KEY") is not None

    def analyze_task(self, task: TaskContext) -> AnalysisResult:
        """Analyse the task and return classification + complexity."""
        # Your logic here
        return AnalysisResult(
            task_class="feature",
            complexity_score=0.7,
            suggested_path_id="B",
            keywords=["implement", "api"],
            provider=self.name,
        )

    def compress_context(self, context: ContextBundle) -> CompressedContext:
        """Compress items to fit within budget_bytes.

        MUST return CompressedContext with compression_ratio = compressed_bytes / original_bytes.
        If compression fails, return all items and ratio=1.0 (no compression).
        Never raise exceptions.
        """
        original_bytes = sum(len(item.encode()) for item in context.items)

        # Your compression logic here
        # (e.g., call external API, apply ML model, etc.)
        compressed_items = context.items[:1]  # Example: keep only first item
        compressed_bytes = len(compressed_items[0].encode())

        return CompressedContext(
            items=compressed_items,
            original_bytes=original_bytes,
            compressed_bytes=compressed_bytes,
            compression_ratio=compressed_bytes / original_bytes
            if original_bytes > 0
            else 1.0,
            provider=self.name,
        )

    def estimate_budget(self, task: TaskContext) -> BudgetEstimate:
        """Estimate context bytes required for the task."""
        # Your estimation logic here
        return BudgetEstimate(
            estimated_bytes=50_000,
            suggested_path_id="B",
            confidence=0.7,
            provider=self.name,
        )
```

**Register your provider:**

```python
from providence_runtime.context import ContextLoader
from providence_runtime.intelligence import ProviderRegistry
from providence_runtime.providers import AstProvider, TfidfProvider

# Create registry with your provider first (highest priority)
registry = ProviderRegistry(
    [
        MyCustomProvider(),  # Your provider — tried first
        AstProvider(),  # Fallback to AST
        TfidfProvider(),  # Fallback to TF-IDF
        # LocalIntelligenceProvider is automatic (always last)
    ]
)

# Use it
loader = ContextLoader(registry=registry)
result = loader.load_result(request)
```

**Key requirements:**

- All methods must be safe to call unconditionally — never raise exceptions
- `available` property allows the registry to skip unavailable providers
- `compression_ratio` MUST be `compressed_bytes / original_bytes`
- At minimum, keep 1 item (never return empty list)

---

## References

- Implementation: `packages/core/providence_runtime/src/providence_runtime/intelligence.py`
- Providers: `packages/core/providence_runtime/src/providence_runtime/providers/`
- Budget zones: [`economy/execution-budget.md`](../../spec/canonical/core/economy/execution-budget.md)
- Efficiency policy: [`economy/efficiency-policy.md`](../../spec/canonical/core/economy/efficiency-policy.md)
