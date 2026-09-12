"""Pluggable Intelligence Providers tests — Phase 5.

Covers:
  - Data type construction and default values
  - LocalIntelligenceProvider.name and .available (always True)
  - analyze_task: task class via keyword matching (bug-fix/feature/refactor/test/docs/unknown)
  - analyze_task: complexity scoring from query length (low/medium/high bands)
  - analyze_task: PATH suggestion table + high-complexity override to C
  - analyze_task: keywords deduplication + provider field
  - compress_context: deduplication of exact-duplicate items
  - compress_context: truncation to budget_bytes
  - compress_context: compression_ratio = 1.0 when already within budget
  - compress_context: empty items list
  - compress_context: provider field
  - estimate_budget: clamped to [5 KB, 85 KB]
  - estimate_budget: confidence = 0.4
  - estimate_budget: PATH suggestion from estimated size
  - estimate_budget: provider field
  - IntelligenceProvider runtime_checkable isinstance() check
  - ProviderRegistry: empty registry falls back to local
  - ProviderRegistry: unavailable provider is skipped → fallback to local
  - ProviderRegistry: first available provider wins
  - ProviderRegistry: active_provider name
  - ProviderRegistry: delegates analyze_task / compress_context / estimate_budget
"""

from __future__ import annotations

import pytest
from providence_runtime.intelligence import (
    _BUDGET_MAX_BYTES,
    _BUDGET_MIN_BYTES,
    _COMPLEXITY_HIGH,
    _COMPLEXITY_LOW,
    _COMPLEXITY_MED,
    _LOCAL_CONFIDENCE,
    AnalysisResult,
    BudgetEstimate,
    CompressedContext,
    ContextBundle,
    IntelligenceProvider,
    LocalIntelligenceProvider,
    ProviderRegistry,
    TaskContext,
)

# ---------------------------------------------------------------------------
# Data type construction
# ---------------------------------------------------------------------------


class TestDataTypes:
    def test_task_context_required_field(self) -> None:
        t = TaskContext(query="fix the bug")
        assert t.query == "fix the bug"

    def test_task_context_defaults(self) -> None:
        t = TaskContext(query="q")
        assert t.path_id == ""
        assert t.context_bytes_loaded is None
        assert t.context_budget_bytes is None

    def test_analysis_result_fields(self) -> None:
        r = AnalysisResult(
            task_class="bug-fix",
            complexity_score=0.2,
            suggested_path_id="A",
            keywords=["fix"],
            provider="local",
        )
        assert r.task_class == "bug-fix"
        assert r.suggested_path_id == "A"
        assert r.provider == "local"

    def test_context_bundle_fields(self) -> None:
        b = ContextBundle(items=["a", "b"], query="q", budget_bytes=1024)
        assert b.budget_bytes == 1024

    def test_compressed_context_fields(self) -> None:
        c = CompressedContext(
            items=["a"],
            original_bytes=100,
            compressed_bytes=80,
            compression_ratio=0.8,
            provider="local",
        )
        assert c.compression_ratio == 0.8

    def test_budget_estimate_fields(self) -> None:
        e = BudgetEstimate(
            estimated_bytes=10240,
            suggested_path_id="A",
            confidence=0.4,
            provider="local",
        )
        assert e.confidence == 0.4


# ---------------------------------------------------------------------------
# LocalIntelligenceProvider — identity
# ---------------------------------------------------------------------------


class TestLocalProviderIdentity:
    def test_name_is_local(self) -> None:
        assert LocalIntelligenceProvider().name == "local"

    def test_always_available(self) -> None:
        assert LocalIntelligenceProvider().available is True

    def test_satisfies_protocol(self) -> None:
        assert isinstance(LocalIntelligenceProvider(), IntelligenceProvider)


class TestIntelligenceProviderProtocolStubs:
    """Protocol method bodies are unreachable stubs; call them directly for coverage."""

    def test_name_stub_returns_none(self) -> None:
        assert IntelligenceProvider.name.fget(None) is None

    def test_available_stub_returns_none(self) -> None:
        assert IntelligenceProvider.available.fget(None) is None

    def test_analyze_task_stub_returns_none(self) -> None:
        assert IntelligenceProvider.analyze_task(None, None) is None

    def test_compress_context_stub_returns_none(self) -> None:
        assert IntelligenceProvider.compress_context(None, None) is None

    def test_estimate_budget_stub_returns_none(self) -> None:
        assert IntelligenceProvider.estimate_budget(None, None) is None


# ---------------------------------------------------------------------------
# LocalIntelligenceProvider — analyze_task task class
# ---------------------------------------------------------------------------


class TestLocalAnalyzeTaskClass:
    def _analyze(self, query: str, path_id: str = "A") -> AnalysisResult:
        return LocalIntelligenceProvider().analyze_task(
            TaskContext(query=query, path_id=path_id)
        )

    def test_bug_fix_keyword_fix(self) -> None:
        result = self._analyze("fix the login error")
        assert result.task_class == "bug-fix"

    def test_bug_fix_keyword_crash(self) -> None:
        result = self._analyze("app crash on startup")
        assert result.task_class == "bug-fix"

    def test_feature_keyword_add(self) -> None:
        result = self._analyze("add export to CSV")
        assert result.task_class == "feature"

    def test_feature_keyword_implement(self) -> None:
        result = self._analyze("implement retry logic")
        assert result.task_class == "feature"

    def test_refactor_keyword(self) -> None:
        result = self._analyze("refactor auth module")
        assert result.task_class == "refactor"

    def test_test_keyword(self) -> None:
        result = self._analyze("test the payment flow")
        assert result.task_class == "test"

    def test_docs_keyword(self) -> None:
        result = self._analyze("document the API endpoints")
        assert result.task_class == "docs"

    def test_unknown_query(self) -> None:
        result = self._analyze("xyzzy quux")
        assert result.task_class == "unknown"

    def test_keywords_populated_on_match(self) -> None:
        result = self._analyze("fix broken login")
        assert len(result.keywords) > 0

    def test_keywords_empty_on_no_match(self) -> None:
        result = self._analyze("xyzzy quux")
        assert result.keywords == []

    def test_provider_is_local(self) -> None:
        result = self._analyze("fix the bug")
        assert result.provider == "local"


# ---------------------------------------------------------------------------
# LocalIntelligenceProvider — analyze_task complexity + PATH suggestion
# ---------------------------------------------------------------------------


class TestLocalAnalyzeComplexityAndPath:
    def _analyze(self, query: str) -> AnalysisResult:
        return LocalIntelligenceProvider().analyze_task(TaskContext(query=query))

    def test_short_query_low_complexity(self) -> None:
        result = self._analyze("fix bug")  # < 50 chars
        assert result.complexity_score == _COMPLEXITY_LOW

    def test_medium_query_medium_complexity(self) -> None:
        # Between 50 and 200 chars
        query = (
            "fix the authentication bug in the login form where tokens expire too early"
        )
        assert 50 <= len(query) <= 200
        result = self._analyze(query)
        assert result.complexity_score == _COMPLEXITY_MED

    def test_long_query_high_complexity(self) -> None:
        query = "fix " + "x" * 200  # > 200 chars
        result = self._analyze(query)
        assert result.complexity_score == _COMPLEXITY_HIGH

    def test_simple_bug_fix_suggests_path_a(self) -> None:
        result = self._analyze("fix bug")  # short + bug-fix → PATH A
        assert result.suggested_path_id == "A"

    def test_high_complexity_any_class_suggests_path_c(self) -> None:
        query = "add " + "x" * 200  # feature keyword but very long → high complexity
        result = self._analyze(query)
        assert result.suggested_path_id == "C"

    def test_unknown_medium_defaults_to_path_b(self) -> None:
        # unknown task class, medium complexity → no table entry → "B"
        query = "xyzzy " + "x" * 60  # medium length
        result = self._analyze(query)
        assert result.task_class == "unknown"
        assert result.suggested_path_id == "B"


# ---------------------------------------------------------------------------
# LocalIntelligenceProvider — compress_context
# ---------------------------------------------------------------------------


class TestLocalCompressContext:
    def _compress(self, items: list[str], budget: int = 10_000) -> CompressedContext:
        bundle = ContextBundle(items=items, query="q", budget_bytes=budget)
        return LocalIntelligenceProvider().compress_context(bundle)

    def test_empty_items(self) -> None:
        result = self._compress([])
        assert result.items == []
        assert result.original_bytes == 0
        assert result.compression_ratio == 1.0

    def test_deduplicates_exact_lines(self) -> None:
        result = self._compress(["a", "b", "a", "b", "c"])
        assert result.items == ["a", "b", "c"]

    def test_within_budget_no_truncation(self) -> None:
        items = ["short item one", "short item two"]
        result = self._compress(items, budget=10_000)
        assert result.items == items
        assert result.compression_ratio == pytest.approx(1.0, rel=1e-2)

    def test_truncates_to_budget_bytes(self) -> None:
        # Each item is ~10 bytes; budget is 15 bytes → only 1 item fits after first
        items = ["0123456789", "0123456789", "0123456789"]
        result = self._compress(items, budget=15)
        assert len(result.items) < len(items)
        assert result.compressed_bytes <= 20  # some slack for the first item

    def test_compression_ratio_less_than_one_when_compressed(self) -> None:
        big_item = "x" * 200
        items = [big_item, big_item, big_item]  # heavy with duplicates
        result = self._compress(items, budget=50)
        assert result.compression_ratio < 1.0

    def test_original_bytes_counts_duplicates(self) -> None:
        items = ["abc", "abc"]  # 3 bytes × 2 = 6 original
        result = self._compress(items, budget=10_000)
        assert result.original_bytes == 6

    def test_provider_is_local(self) -> None:
        result = self._compress(["a", "b"])
        assert result.provider == "local"


# ---------------------------------------------------------------------------
# LocalIntelligenceProvider — estimate_budget
# ---------------------------------------------------------------------------


class TestLocalEstimateBudget:
    def _estimate(self, query: str) -> BudgetEstimate:
        return LocalIntelligenceProvider().estimate_budget(TaskContext(query=query))

    def test_returns_positive_bytes(self) -> None:
        result = self._estimate("fix the bug")
        assert result.estimated_bytes > 0

    def test_confidence_is_low(self) -> None:
        result = self._estimate("fix the bug")
        assert result.confidence == pytest.approx(_LOCAL_CONFIDENCE)

    def test_provider_is_local(self) -> None:
        result = self._estimate("fix the bug")
        assert result.provider == "local"

    def test_clamps_to_minimum(self) -> None:
        # Very short query → raw estimate below 5 KB floor
        result = self._estimate("x")
        assert result.estimated_bytes == _BUDGET_MIN_BYTES

    def test_clamps_to_maximum(self) -> None:
        # Very long query → raw estimate above 85 KB ceiling
        result = self._estimate("x" * 100_000)
        assert result.estimated_bytes == _BUDGET_MAX_BYTES

    def test_suggests_path_a_for_small_estimate(self) -> None:
        # Short query → small estimate → PATH A
        result = self._estimate("fix")
        assert result.suggested_path_id == "A"

    def test_suggests_path_id_is_set(self) -> None:
        result = self._estimate("fix the bug")
        assert result.suggested_path_id in {"A", "B", "C", "D"}


# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------


class _UnavailableProvider:
    """Test stub — always unavailable."""

    @property
    def name(self) -> str:
        return "unavailable"

    @property
    def available(self) -> bool:
        return False

    def analyze_task(self, task: TaskContext) -> AnalysisResult:
        raise AssertionError("should not be called")

    def compress_context(self, context: ContextBundle) -> CompressedContext:
        raise AssertionError("should not be called")

    def estimate_budget(self, task: TaskContext) -> BudgetEstimate:
        raise AssertionError("should not be called")


class _NamedProvider:
    """Test stub — available, returns a distinct provider name."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def available(self) -> bool:
        return True

    def analyze_task(self, task: TaskContext) -> AnalysisResult:
        return AnalysisResult(
            task_class="unknown",
            complexity_score=0.5,
            suggested_path_id="B",
            keywords=[],
            provider=self._name,
        )

    def compress_context(self, context: ContextBundle) -> CompressedContext:
        b = sum(len(i.encode()) for i in context.items)
        return CompressedContext(
            items=context.items,
            original_bytes=b,
            compressed_bytes=b,
            compression_ratio=1.0,
            provider=self._name,
        )

    def estimate_budget(self, task: TaskContext) -> BudgetEstimate:
        return BudgetEstimate(
            estimated_bytes=10_000,
            suggested_path_id="A",
            confidence=0.9,
            provider=self._name,
        )


class TestProviderRegistry:
    def test_empty_registry_active_provider_is_local(self) -> None:
        reg = ProviderRegistry()
        assert reg.active_provider == "local"

    def test_empty_registry_analyze_task_works(self) -> None:
        reg = ProviderRegistry()
        result = reg.analyze_task(TaskContext(query="fix bug"))
        assert result.provider == "local"

    def test_empty_registry_compress_context_works(self) -> None:
        reg = ProviderRegistry()
        bundle = ContextBundle(items=["a", "b"], query="q", budget_bytes=1024)
        result = reg.compress_context(bundle)
        assert result.provider == "local"

    def test_empty_registry_estimate_budget_works(self) -> None:
        reg = ProviderRegistry()
        result = reg.estimate_budget(TaskContext(query="fix bug"))
        assert result.provider == "local"

    def test_unavailable_provider_falls_back_to_local(self) -> None:
        reg = ProviderRegistry(providers=[_UnavailableProvider()])  # type: ignore[list-item]
        assert reg.active_provider == "local"
        # Must not raise
        result = reg.analyze_task(TaskContext(query="fix bug"))
        assert result.provider == "local"

    def test_available_provider_is_used(self) -> None:
        reg = ProviderRegistry(providers=[_NamedProvider("semantic")])  # type: ignore[list-item]
        assert reg.active_provider == "semantic"

    def test_first_available_provider_wins(self) -> None:
        reg = ProviderRegistry(
            providers=[  # type: ignore[list-item]
                _UnavailableProvider(),
                _NamedProvider("ast"),
                _NamedProvider("semantic"),
            ]
        )
        assert reg.active_provider == "ast"

    def test_registry_delegates_analyze_task_to_provider(self) -> None:
        reg = ProviderRegistry(providers=[_NamedProvider("semantic")])  # type: ignore[list-item]
        result = reg.analyze_task(TaskContext(query="fix bug"))
        assert result.provider == "semantic"

    def test_registry_delegates_compress_context_to_provider(self) -> None:
        reg = ProviderRegistry(providers=[_NamedProvider("semantic")])  # type: ignore[list-item]
        bundle = ContextBundle(items=["a"], query="q", budget_bytes=1024)
        result = reg.compress_context(bundle)
        assert result.provider == "semantic"

    def test_registry_delegates_estimate_budget_to_provider(self) -> None:
        reg = ProviderRegistry(providers=[_NamedProvider("semantic")])  # type: ignore[list-item]
        result = reg.estimate_budget(TaskContext(query="fix bug"))
        assert result.provider == "semantic"

    def test_all_unavailable_falls_back_to_local(self) -> None:
        reg = ProviderRegistry(
            providers=[_UnavailableProvider(), _UnavailableProvider()]  # type: ignore[list-item]
        )
        assert reg.active_provider == "local"
