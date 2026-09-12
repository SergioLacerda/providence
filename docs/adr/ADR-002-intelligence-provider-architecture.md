# ADR-002 — Pluggable Intelligence Provider Architecture

**Status:** Accepted
**Date:** 2026-05-11
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

Phase 5/6 introduced automated context compression to enforce budget zone governance. The system must support
multiple compression strategies:

- **TF-IDF similarity ranking** — keep items most relevant to the query
- **Python AST deduplication** — structural code deduplication
- **HTTP delegation** — external service integration (e.g., ML models, semantic analysis)
- **Local heuristic** — simple dedup + truncation (guaranteed fallback)

Embedding any single strategy would:

1. Prevent extension and limit future improvements
2. Break the graceful degradation guarantee (if external service fails, system crashes)
3. Create tight coupling between governance layer and implementation details

The system needs:

- **Pluggability:** Third-party providers without modifying core
- **Graceful degradation:** Guaranteed fallback when external providers fail
- **Transparent integration:** Compression happens automatically at YELLOW zone without caller awareness

---

## Decision

Implement a **pluggable `IntelligenceProvider` protocol** with a **cascading `ProviderRegistry`**.

### Architecture

```python
@runtime_checkable
class IntelligenceProvider(Protocol):
    """All providers implement this interface."""

    @property
    def name(self) -> str: ...  # e.g., "tfidf", "http-external", "local"

    @property
    def available(self) -> bool: ...  # e.g., check env var, network health

    def analyze_task(task: TaskContext) -> AnalysisResult: ...
    def compress_context(bundle: ContextBundle) -> CompressedContext: ...
    def estimate_budget(task: TaskContext) -> BudgetEstimate: ...
```

### Provider Registry — Cascading Priority

```python
class ProviderRegistry:
    """Tries providers in order; falls back to Local if all fail."""

    def __init__(self, providers: list[IntelligenceProvider]):
        self._providers = providers
        self._local = LocalIntelligenceProvider()  # Always available

    def compress_context(self, bundle: ContextBundle) -> CompressedContext:
        """Try each provider until one succeeds. Local is guaranteed fallback."""
        for provider in self._providers:
            if provider.available:
                try:
                    return provider.compress_context(bundle)  # Success
                except Exception:
                    logger.debug(f"Provider {provider.name} failed; trying next")
        # Fallback
        return self._local.compress_context(bundle)
```

**Default priority chain:**

1. `HttpProvider` — if `SDD_INTELLIGENCE_URL` env var set and endpoint healthy
2. `AstProvider` — always available (gracefully degrades on non-Python input)
3. `TfidfProvider` — always available (pure Python, no external deps)
4. `LocalIntelligenceProvider` — guaranteed fallback (built-in, always succeeds)

### Compression Ratio Convention — Normative

All providers MUST follow:

```
compression_ratio = compressed_bytes / original_bytes
```

| Value | Meaning |
|-------|---------|
| 1.0 | No compression (output = input) |
| < 1.0 | Compression applied (e.g., 0.5 = 50% reduction) |
| > 1.0 | **INVALID** — must never occur |

**Enforcement:** `ContextLoader` checks `if compressed.compression_ratio < 1.0:` before using compressed result.
Providers that violate this convention break the compression path and are silently skipped.

---

## Consequences

### Positive

1. **Extensibility:** New providers can be added without modifying `ContextLoader` or registry
2. **Graceful degradation:** Network failure, misconfiguration, or provider bug → falls back to Local
3. **Separation of concerns:** Compression strategy is isolated from budget enforcement
4. **Testing:** Each provider can be tested independently; registry can be mocked

### Negative

1. **Protocol vs. ABC:** Using Protocol means no enforcement of implementation. A class could claim to be a
   provider but fail at runtime. Mitigation: runtime checks + integration tests.
2. **Ordering dependency:** If a faulty provider is registered before Local, it must fail gracefully. Mitigation:
   providers are responsible for never raising exceptions.

### How to Extend

Implement the protocol and register:

```python
class MySemanticProvider:
    @property
    def name(self) -> str:
        return "semantic-analysis"

    @property
    def available(self) -> bool:
        return os.environ.get("SEMANTIC_API_KEY") is not None

    def compress_context(self, bundle: ContextBundle) -> CompressedContext:
        # Call semantic API, return CompressedContext
        # Ensure: compression_ratio = compressed_bytes / original_bytes
        ...


# Register
loader = ContextLoader(
    registry=ProviderRegistry(
        [
            MySemanticProvider(),  # Try first
            HttpProvider(),  # Fallback to HTTP
            AstProvider(),  # Fallback to AST
            TfidfProvider(),  # Fallback to TF-IDF
        ]
    )
)
```

---

## Alternatives Considered and Rejected

### 1. Single `if/else` Strategy Selector

```python
if compression_strategy == "tfidf":
    result = tfidf_compress(bundle)
elif compression_strategy == "http":
    result = http_compress(bundle)
else:
    result = local_compress(bundle)
```

**Rejected:** Rigid. Every new strategy requires code change. Poor separation of concerns.

### 2. Abstract Base Class (`ABC`)

```python
class IntelligenceProvider(ABC):
    @abstractmethod
    def compress_context(self, bundle): ...
```

**Rejected:** Requires inheritance coupling. Python Protocol is sufficient and more flexible.
Avoids the "classic" ABC overhead when duck-typing is sufficient.

### 3. Factory Pattern (`create_provider()`)

```python
def create_provider(name: str) -> IntelligenceProvider:
    if name == "tfidf":
        return TfidfProvider()
    elif name == "http":
        return HttpProvider()
    ...
```

**Rejected:** Centralizes knowledge of all providers. Same inflexibility as single `if/else`.

---

## Implementation Details

- **Protocol:** `providence_runtime/intelligence.py:IntelligenceProvider`
- **Registry:** `providence_runtime/intelligence.py:ProviderRegistry`
- **Built-in providers:** `providence_runtime/providers/{http,ast,tfidf,local}_provider.py`
- **Integration:** `providence_runtime/context.py:ContextLoader` attempts compression in YELLOW zone
- **Tests:** `packages/core/providence_runtime/tests/test_providers.py` (unit tests per provider)
- **Integration tests:** `packages/core/providence_runtime/tests/test_compression_trigger.py`

---

## References

- Technical guide: [docs/guides/TECHNICAL_GUIDE.md](../guides/TECHNICAL_GUIDE.md#token-economy)
- Compression mechanics: see `docs/cognition/context-loading/COMPRESSION.md`
- Budget zones: [docs/spec/canonical/core/economy/execution-budget.md](../spec/canonical/core/economy/execution-budget.md)
- Efficiency policy: [docs/spec/canonical/core/economy/efficiency-policy.md](../spec/canonical/core/economy/efficiency-policy.md)
- Mandate M005: see `docs/spec/canonical/core/mandates/M005_TOKEN_ECONOMY.md`

---

## Sign-off

✅ Accepted — 2026-05-11
