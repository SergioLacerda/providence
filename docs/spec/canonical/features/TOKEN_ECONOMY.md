# 💰 TOKEN_ECONOMY — LLM Token Governance & Context Compression

## 🎯 Purpose

Implement a comprehensive token economy system that:

1. Captures and tracks LLM token consumption (input + output)
2. Monitors context budget utilization across 4 execution PATHs
3. Automatically compresses context when budget usage exceeds safe thresholds
4. Provides intelligent analysis and budget estimation via pluggable providers
5. Caches context to avoid redundant loads and compression

---

## 🔒 Core Principles

> Token consumption is a first-class concern, not an afterthought.
> Context inflation must be visible and governed.
> Compression must degrade gracefully and never block execution.
> Budget zones (GREEN/YELLOW/RED/BREACH) drive mandatory actions.

---

## 📦 Subsystems

### 1. LLM Token Capture (`llm.py`)

**Purpose:** Instrument LLM API calls to capture token usage for observability and budget enforcement.

**API:**

```python
@dataclass
class TokenCounts:
    tokens_input: int
    tokens_output: int
    @property
    tokens_total: int  # computed

class LLMTokenCapture(Protocol):
    def capture_from_response(response: Any) -> TokenCounts | None: ...
    def capture_from_env() -> TokenCounts | None: ...

class SimulatedTokenCapture:
    """Reads from SDD_TOKENS_INPUT / SDD_TOKENS_OUTPUT env vars for CI/test."""
```

**Usage:**

```bash
# Pass tokens explicitly
providence ask "query" --full --tokens-input 150 --tokens-output 50

# Or via environment variables (picked up automatically if --tokens-* not provided)
SDD_TOKENS_INPUT=150 SDD_TOKENS_OUTPUT=50 providence ask "query" --full
```

**Integration:**

- `ask --full` wires token capture into `_emit_ask_telemetry()`
- Tokens populate `RuntimeEvent.tokens_input`, `tokens_output`, `tokens_total`
- Token ceilings per PATH enforced in `efficiency-policy.md`

---

### 2. Context Cache (`cache.py`)

**Purpose:** Reduce redundant context loads via in-memory LRU caching with TTL.

**Design:**

- **Capacity:** 128 entries
- **TTL:** 5 minutes (300 seconds)
- **Key:** SHA-256 hash of `(artifact_id, query, max_items, item_types)`
- **Eviction:** O(n) min-timestamp when at capacity (replaces oldest entry)
- **Bypass:** Cache hits bypass compression re-check → budget tracking reflects cached utilization

**API:**

```python
cache = get_context_cache()
stats = cache.stats()  # hit_count, miss_count, hit_rate_pct, entries, max_size

# Applied to ContextLoader.load_result via @cached_load decorator
```

**Economy Implications:**

- Cache hit returns stale `context_bytes_loaded` from previous computation
- If cached during GREEN zone, returned as-is even if now in YELLOW zone
- Compression not re-attempted on cache hit
- **Policy:** Assume cache accuracy; always check utilization if budget concerns arise

---

### 3. Intelligence Provider System (`intelligence.py`, `providers/`)

**Purpose:** Pluggable providers that analyze tasks, compress context, and estimate budgets.

**Core Protocol:**

```python
class IntelligenceProvider(Protocol):
    @property
    available: bool: ...  # can this provider be used?

    @property
    name: str: ...  # e.g., "http", "ast", "tfidf", "local"

    def analyze_task(task: TaskContext) -> AnalysisResult: ...
    def compress_context(bundle: ContextBundle) -> CompressedContext: ...
    def estimate_budget(task: TaskContext) -> BudgetEstimate: ...
```

**Data Types:**

```python
@dataclass
class TaskContext:
    query: str
    agent_role: str = ""


@dataclass
class AnalysisResult:
    provider: str
    task_class: str  # e.g., "python_code", "governance_doc", "unknown"
    complexity_score: float  # 0.0–1.0
    suggested_path_id: str  # "A" | "B" | "C" | "D"
    keywords: list[str]


@dataclass
class ContextBundle:
    items: list[str]
    query: str
    budget_bytes: int


@dataclass
class CompressedContext:
    items: list[str]
    original_bytes: int
    compressed_bytes: int
    compression_ratio: float  # compressed_bytes / original_bytes (< 1.0 = reduced)
    provider: str


@dataclass
class BudgetEstimate:
    provider: str
    estimated_bytes: int
    suggested_path_id: str
    confidence: float  # 0.0–1.0
```

**Compression Ratio Convention:**

- `compression_ratio = compressed_bytes / original_bytes`
- Value 1.0 → no compression
- Value < 1.0 → compression successful (e.g., 0.5 = 50% reduction)
- All built-in providers follow this convention

---

### 4. Built-In Providers

#### 4.1 `HttpProvider` — External Service Delegation

**Strategy:** POST JSON to remote service endpoint.

**Environment:** `SDD_INTELLIGENCE_URL` (e.g., `http://localhost:8000`)

**Endpoints expected:**

- `POST /analyze` — task analysis
- `POST /compress` — context compression
- `POST /estimate` — budget estimation

**Availability:** Only when env var is set AND endpoint responds 200 on health check.

**Graceful degradation:** Network failure → returns degraded result (no compression, max budget estimate), never raises.

**Implementation:** `packages/core/providence_runtime/src/providence_runtime/providers/http_provider.py`

---

#### 4.2 `AstProvider` — Python AST Analysis

**Strategy:** Parse Python code, count syntactic elements (ClassDef, FunctionDef, Import nodes).

**Compression:** Exact-match deduplication of items, then budget-fit truncation.

**Availability:** Always (degrades gracefully on non-Python input).

**Complexity scoring:** `node_count / 100` (capped at 1.0).

**Implementation:** `packages/core/providence_runtime/src/providence_runtime/providers/ast_provider.py`

---

#### 4.3 `TfidfProvider` — TF-IDF Similarity Ranking

**Strategy:** Pure Python TF-IDF (no ML deps): use `collections.Counter` and cosine similarity.

**Compression:** Score items by TF-IDF relevance to query, remove lowest-scoring items until budget is met.

**Availability:** Always.

**Budget estimation:** `query_length * 8 bytes` heuristic.

**Implementation:** `packages/core/providence_runtime/src/providence_runtime/providers/tfidf_provider.py`

---

#### 4.4 `LocalIntelligenceProvider` — Fallback (Built-In)

**Strategy:** Keyword matching, deduplication, budget-fit truncation.

**Always available:** Guaranteed fallback when all other providers fail.

**Compression:**

1. Deduplicate identical items
2. Sort by length (longest first, preserve relevance-ordered items)
3. Truncate to fit budget
4. Always keep at least 1 item

**Implementation:** `packages/core/providence_runtime/src/providence_runtime/intelligence.py`

---

### 5. ProviderRegistry — Cascading Provider Chain

**Purpose:** Automatic provider selection and fallback.

**Default priority:**

1. `HttpProvider` — if env var set and available
2. `AstProvider` — always available
3. `TfidfProvider` — always available
4. `LocalIntelligenceProvider` — final fallback (always)

**Contract:**

- Tries providers in order; uses first that is `available`
- If provider fails (exception), logs and tries next
- Compression ALWAYS succeeds (degradation guaranteed)
- Never raises exception on `compress_context()`

**Implementation:** `packages/core/providence_runtime/src/providence_runtime/intelligence.py:ProviderRegistry`

---

## 🔋 Integration with `ContextLoader`

The `ContextLoader` wires the economy system into context loading:

```python
loader = ContextLoader(registry=ProviderRegistry([...]))
request = ContextRequest(
    query="...",
    max_items=5,
    budget_utilization_pct=75.0,  # current utilization
)
result = loader.load_result(request)
# result.compression_ratio populated if compression applied
# result.bytes_loaded reflects post-compression size
```

**YELLOW Zone Behavior (70–90% utilization):**

- Computes target budget: `original_bytes * (70 / utilization_pct)`
- Calls `registry.compress_context(bundle)` with target budget
- If `compression_ratio < 1.0`, uses compressed result
- If `compression_ratio >= 1.0` (no compression), emits `economy.compression.skip` event

**BREACH Behavior (≥100% utilization):**

- Raises `BudgetBreachError` (exception, not just event)
- No further context loading permitted
- Caller must catch and escalate to human checkpoint

---

## 🚨 BudgetBreachError Contract

**Exception type:** `packages/core/providence_runtime/src/providence_runtime/context.py:BudgetBreachError`

**When raised:** `ContextLoader.load_result()` when `budget_utilization_pct >= 100`

**Caller responsibility:**

1. Catch the exception
2. Log `error.utilization_pct` and `error.path_id` for audit
3. Escalate to human checkpoint
4. Do NOT attempt further `ContextLoader.load_result()` calls

**Example:**

```python
from providence_runtime.context import ContextLoader, BudgetBreachError, ContextRequest

loader = ContextLoader()
request = ContextRequest(query="...", budget_utilization_pct=105.0)
try:
    result = loader.load_result(request)
except BudgetBreachError as err:
    logger.error(
        "Budget breach on %s: utilization %.1f%% — escalating",
        err.path_id,
        err.utilization_pct,
    )
    raise  # escalate to caller
```

---

## 📊 RuntimeEvent Economy Fields

All token economy data flows into `RuntimeEvent` telemetry:

| Field | Description |
|-------|-------------|
| `tokens_input` | LLM input tokens (from `SimulatedTokenCapture` or API) |
| `tokens_output` | LLM output tokens |
| `tokens_total` | Computed as `tokens_input + tokens_output` |
| `context_bytes_loaded` | Total bytes loaded into context (post-compression if applicable) |
| `context_budget_bytes` | Budget ceiling for active PATH (derived from `path_id`) |
| `budget_utilization_pct` | Derived: `(context_bytes_loaded / context_budget_bytes) * 100` |
| `compression_ratio` | Populated by ContextLoader when compression applied |
| `path_id` | Active execution PATH: "A" \| "B" \| "C" \| "D" |

**Auto-enrichment:** `TelemetrySink._enrich_economy()` auto-derives budget bytes and utilization pct from these fields.

---

## 🔗 References

- `→ economy/execution-budget.md` — budget ceilings, zones, circuit-breaker rules
- `→ economy/efficiency-policy.md` — compression obligations, retry/reflection ceilings
- `→ economy/metrics.md` — canonical field names and OTEL attributes
- `→ packages/core/providence_runtime/src/providence_runtime/telemetry.py` — RuntimeEvent schema
- `→ packages/core/providence_runtime/src/providence_runtime/context.py` — ContextLoader integration
