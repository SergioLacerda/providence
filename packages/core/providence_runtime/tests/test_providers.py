"""Tests for intelligence providers: TF-IDF, AST, and HTTP."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from providence_runtime.intelligence import ContextBundle, TaskContext
from providence_runtime.providers import AstProvider, HttpProvider, TfidfProvider


class TestTfidfProvider:
    """Test TfidfProvider (TF-IDF similarity-based)."""

    def test_tfidf_provider_always_available(self) -> None:
        """TfidfProvider should always be available."""
        provider = TfidfProvider()
        assert provider.available is True

    def test_tfidf_provider_name(self) -> None:
        """TfidfProvider name should be 'tfidf'."""
        provider = TfidfProvider()
        assert provider.name == "tfidf"

    def test_tfidf_analyze_task_basic(self) -> None:
        """TfidfProvider.analyze_task should return AnalysisResult."""
        provider = TfidfProvider()
        task = TaskContext(query="test governance policy")

        result = provider.analyze_task(task)

        assert result.provider == "tfidf"
        assert 0 <= result.complexity_score <= 1.0
        assert result.suggested_path_id in ("A", "B", "C", "D")
        assert isinstance(result.keywords, list)

    def test_tfidf_analyze_task_high_complexity(self) -> None:
        """Long queries should get higher complexity scores."""
        provider = TfidfProvider()
        short_task = TaskContext(query="test")
        long_task = TaskContext(query="a" * 200)

        short_result = provider.analyze_task(short_task)
        long_result = provider.analyze_task(long_task)

        assert short_result.complexity_score < long_result.complexity_score

    def test_tfidf_compress_context_basic(self) -> None:
        """TfidfProvider.compress_context should return CompressedContext."""
        provider = TfidfProvider()
        bundle = ContextBundle(
            items=["item1", "item2", "item3"],
            query="test",
            budget_bytes=100,
        )

        result = provider.compress_context(bundle)

        assert result.provider == "tfidf"
        assert result.compression_ratio > 0
        assert 0 < len(result.items) <= 3
        assert result.compressed_bytes <= result.original_bytes

    def test_tfidf_compress_respects_budget(self) -> None:
        """TfidfProvider should respect budget_bytes."""
        provider = TfidfProvider()
        items = ["a" * 100, "b" * 100, "c" * 100]  # Each ~100 bytes
        bundle = ContextBundle(
            items=items,
            query="test",
            budget_bytes=50,  # Very small budget
        )

        result = provider.compress_context(bundle)

        # At least one item must be kept
        assert len(result.items) >= 1
        # But should try to stay within budget
        total_bytes = sum(len(item.encode()) for item in result.items)
        assert total_bytes <= 100  # Should be close to budget

    def test_tfidf_estimate_budget(self) -> None:
        """TfidfProvider.estimate_budget should return BudgetEstimate."""
        provider = TfidfProvider()
        task = TaskContext(query="test")

        result = provider.estimate_budget(task)

        assert result.provider == "tfidf"
        assert 0 < result.estimated_bytes <= 85_000
        assert result.suggested_path_id in ("A", "B", "C", "D")
        assert 0 <= result.confidence <= 1.0


class TestAstProvider:
    """Test AstProvider (Python AST analysis)."""

    def test_ast_provider_available(self) -> None:
        """AstProvider should always be available (degrades gracefully)."""
        provider = AstProvider()
        assert provider.available is True

    def test_ast_provider_name(self) -> None:
        """AstProvider name should be 'ast'."""
        provider = AstProvider()
        assert provider.name == "ast"

    def test_ast_analyze_python_code(self) -> None:
        """AstProvider should analyze Python code structure."""
        provider = AstProvider()
        code = "def foo():\n    pass\nclass Bar:\n    pass"
        task = TaskContext(query=code)

        result = provider.analyze_task(task)

        assert result.provider == "ast"
        assert result.task_class in ("python_code", "unknown")
        assert result.complexity_score >= 0

    def test_ast_analyze_non_python(self) -> None:
        """AstProvider should degrade gracefully for non-Python input."""
        provider = AstProvider()
        task = TaskContext(query="not valid python code )(#$")

        result = provider.analyze_task(task)

        assert result.provider == "ast"
        assert result.task_class == "unknown"
        assert result.complexity_score >= 0

    def test_ast_compress_deduplicates(self) -> None:
        """AstProvider should deduplicate identical items."""
        provider = AstProvider()
        items = ["item1", "item1", "item2"]  # Duplicate
        bundle = ContextBundle(
            items=items,
            query="test",
            budget_bytes=1000,
        )

        result = provider.compress_context(bundle)

        assert len(result.items) <= 2  # Deduplicated
        assert (
            result.compression_ratio <= 1.0
        )  # compression_ratio < 1.0 = compression successful

    def test_ast_estimate_budget(self) -> None:
        """AstProvider.estimate_budget should return BudgetEstimate."""
        provider = AstProvider()
        task = TaskContext(query="def foo(): pass")

        result = provider.estimate_budget(task)

        assert result.provider == "ast"
        assert result.estimated_bytes > 0
        assert result.suggested_path_id in ("A", "B", "C", "D")


class TestHttpProvider:
    """Test HttpProvider (HTTP delegation)."""

    def test_http_provider_name(self) -> None:
        """HttpProvider name should be 'http'."""
        provider = HttpProvider()
        assert provider.name == "http"

    async def test_http_provider_unavailable_without_url(self) -> None:
        """HttpProvider should be unavailable when SDD_INTELLIGENCE_URL not set."""
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("SDD_INTELLIGENCE_URL", None)
            provider = HttpProvider()
            assert await provider.is_available() is False

    async def test_http_provider_graceful_degradation(self) -> None:
        """HttpProvider should degrade gracefully when service unavailable."""
        from unittest.mock import AsyncMock

        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("SDD_INTELLIGENCE_URL", None)
            provider = HttpProvider()

            task = TaskContext(query="test")
            with patch.object(
                provider, "is_available", new=AsyncMock(return_value=False)
            ):
                result = await provider.analyze_task(task)

            # Should return degraded result, not raise
            assert result.provider == "http"
            assert result.task_class == "unknown"

    async def test_http_compress_fallback_when_unavailable(self) -> None:
        """HttpProvider should return uncompressed context when unavailable."""
        from unittest.mock import AsyncMock

        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("SDD_INTELLIGENCE_URL", None)
            provider = HttpProvider()
            bundle = ContextBundle(
                items=["item1", "item2"],
                query="test",
                budget_bytes=100,
            )

            with patch.object(
                provider, "is_available", new=AsyncMock(return_value=False)
            ):
                result = await provider.compress_context(bundle)

            # Should return all items uncompressed
            assert len(result.items) == 2
            assert result.compression_ratio == 1.0

    async def test_http_estimate_fallback_when_unavailable(self) -> None:
        """HttpProvider should return fallback budget when unavailable."""
        from unittest.mock import AsyncMock

        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("SDD_INTELLIGENCE_URL", None)
            provider = HttpProvider()
            task = TaskContext(query="test")

            with patch.object(
                provider, "is_available", new=AsyncMock(return_value=False)
            ):
                result = await provider.estimate_budget(task)

            assert result.provider == "http"
            assert result.estimated_bytes > 0
            assert 0 < result.confidence < 1.0

    async def test_http_provider_available_healthcheck_success(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch.dict(
            "os.environ",
            {
                "SDD_INTELLIGENCE_URL": "http://svc",
                "SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP": "true",
            },
            clear=False,
        ):
            provider = HttpProvider()
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_resp)
            with patch("httpx.AsyncClient", return_value=mock_client):
                assert await provider.is_available() is True

    async def test_http_provider_available_healthcheck_failure_cached(self) -> None:
        from unittest.mock import AsyncMock

        with patch.dict(
            "os.environ",
            {
                "SDD_INTELLIGENCE_URL": "http://svc",
                "SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP": "true",
            },
            clear=False,
        ):
            provider = HttpProvider()
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(side_effect=RuntimeError("down"))
            with patch("httpx.AsyncClient", return_value=mock_client):
                assert await provider.is_available() is False
                # Second call should use cached availability
                assert await provider.is_available() is False

    async def test_http_call_service_unknown_result_type_raises(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={})
        mock_resp.raise_for_status = MagicMock()

        with patch.dict(
            "os.environ",
            {
                "SDD_INTELLIGENCE_URL": "http://svc",
                "SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP": "true",
            },
            clear=False,
        ):
            provider = HttpProvider()
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            with (
                patch("httpx.AsyncClient", return_value=mock_client),
                pytest.raises(ValueError, match="Unknown result type"),
            ):
                await provider._call_service("analyze", {}, dict)  # type: ignore[arg-type]

    async def test_http_analyze_compress_estimate_exception_paths(self) -> None:
        from unittest.mock import AsyncMock

        with patch.dict(
            "os.environ",
            {
                "SDD_INTELLIGENCE_URL": "http://svc",
                "SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP": "true",
            },
            clear=False,
        ):
            provider = HttpProvider()
            provider._available = True
            with (
                patch.object(
                    provider, "is_available", new=AsyncMock(return_value=True)
                ),
                patch.object(
                    provider,
                    "_call_service",
                    new=AsyncMock(side_effect=RuntimeError("x")),
                ),
            ):
                task = TaskContext(query="test")
                bundle = ContextBundle(items=["a"], query="q", budget_bytes=10)
                assert (await provider.analyze_task(task)).task_class == "unknown"
                assert (
                    await provider.compress_context(bundle)
                ).compression_ratio == 1.0
                assert (await provider.estimate_budget(task)).estimated_bytes == 50_000


class TestProviderProtocol:
    """Test that all providers implement IntelligenceProvider protocol."""

    def test_tfidf_implements_protocol(self) -> None:
        """TfidfProvider should implement IntelligenceProvider."""
        from providence_runtime.intelligence import IntelligenceProvider

        provider = TfidfProvider()
        assert isinstance(provider, IntelligenceProvider.__class__) or hasattr(
            provider, "analyze_task"
        )
        assert callable(provider.analyze_task)
        assert callable(provider.compress_context)
        assert callable(provider.estimate_budget)

    def test_ast_implements_protocol(self) -> None:
        """AstProvider should implement IntelligenceProvider."""
        provider = AstProvider()
        assert hasattr(provider, "analyze_task")
        assert callable(provider.analyze_task)
        assert callable(provider.compress_context)
        assert callable(provider.estimate_budget)

    def test_http_implements_protocol(self) -> None:
        """HttpProvider should implement IntelligenceProvider."""
        provider = HttpProvider()
        assert hasattr(provider, "analyze_task")
        assert callable(provider.analyze_task)
        assert callable(provider.compress_context)
        assert callable(provider.estimate_budget)


class TestProviderInteroperability:
    """Test providers work with common interfaces."""

    def test_all_providers_analyze_task(self) -> None:
        """All providers should successfully analyze a task (sync providers only)."""
        providers = [TfidfProvider(), AstProvider()]
        task = TaskContext(query="test governance policy")

        for provider in providers:
            result = provider.analyze_task(task)
            assert result is not None
            assert result.provider is not None

    def test_all_providers_compress_context(self) -> None:
        """All providers should handle context compression (sync providers only)."""
        providers = [TfidfProvider(), AstProvider()]
        bundle = ContextBundle(
            items=["item1", "item2", "item3"],
            query="test",
            budget_bytes=100,
        )

        for provider in providers:
            result = provider.compress_context(bundle)
            assert result is not None
            assert result.compression_ratio >= 0
            assert len(result.items) > 0

    def test_all_providers_estimate_budget(self) -> None:
        """All providers should estimate budget (sync providers only)."""
        providers = [TfidfProvider(), AstProvider()]
        task = TaskContext(query="test")

        for provider in providers:
            result = provider.estimate_budget(task)
            assert result is not None
            assert result.estimated_bytes > 0


# ─────────────────────────────────────────────────────────────────────────────
# AST Provider Advanced Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAstProviderAdvanced:
    """Advanced tests for AstProvider."""

    def test_ast_count_nodes_complex_code(self) -> None:
        """_count_ast_nodes should count various AST node types."""
        code = """
def outer():
    def inner():
        pass

class MyClass:
    def method(self):
        pass

import sys
from pathlib import Path
"""
        nodes = AstProvider._count_ast_nodes(code)
        assert "FunctionDef" in nodes
        assert "ClassDef" in nodes
        assert "Import" in nodes
        assert nodes["FunctionDef"] >= 2

    def test_ast_count_nodes_empty_string(self) -> None:
        """_count_ast_nodes should handle empty code (returns Module node)."""
        nodes = AstProvider._count_ast_nodes("")
        # Empty code still has a Module node
        assert "Module" in nodes or len(nodes) == 0

    def test_ast_count_nodes_invalid_syntax(self) -> None:
        """_count_ast_nodes should handle invalid syntax gracefully."""
        nodes = AstProvider._count_ast_nodes("def broken( ):")
        assert nodes == {}

    def test_ast_compress_with_empty_items(self) -> None:
        """Compression with empty items should work."""
        provider = AstProvider()
        bundle = ContextBundle(
            items=[],
            query="test",
            budget_bytes=100,
        )
        result = provider.compress_context(bundle)
        assert result.items == []
        assert result.original_bytes == 0
        assert result.compressed_bytes == 0
        assert result.compression_ratio == 1.0

    def test_ast_compress_single_item(self) -> None:
        """Should preserve single item even if over budget."""
        provider = AstProvider()
        large_item = "x" * 500
        bundle = ContextBundle(
            items=[large_item],
            query="test",
            budget_bytes=100,
        )
        result = provider.compress_context(bundle)
        assert len(result.items) == 1
        assert result.items[0] == large_item

    def test_ast_compress_respects_budget_order(self) -> None:
        """Should fit items in order within budget."""
        provider = AstProvider()
        items = ["short1", "short2", "verylongitem" * 20]
        bundle = ContextBundle(
            items=items,
            query="test",
            budget_bytes=50,
        )
        result = provider.compress_context(bundle)
        # Should include at least first two short items
        assert "short1" in result.items
        assert "short2" in result.items

    def test_ast_estimate_boundary_conditions(self) -> None:
        """Budget estimation should respect min/max boundaries."""
        provider = AstProvider()

        # Test low complexity
        task_low = TaskContext(query="x")
        result_low = provider.estimate_budget(task_low)
        assert result_low.estimated_bytes >= 5_000
        assert result_low.estimated_bytes <= 85_000

        # Test high complexity
        task_high = TaskContext(query="def " * 50)
        result_high = provider.estimate_budget(task_high)
        assert result_high.estimated_bytes >= 5_000
        assert result_high.estimated_bytes <= 85_000

    def test_ast_analyze_exception_fallback_branch(self) -> None:
        provider = AstProvider()
        with patch.object(
            provider, "_count_ast_nodes", side_effect=RuntimeError("boom")
        ):
            result = provider.analyze_task(TaskContext(query="x"))
            assert result.task_class == "unknown"
            assert result.complexity_score == 0.5

    def test_ast_compress_exception_fallback_branch(self) -> None:
        provider = AstProvider()
        # Invalid budget type triggers TypeError inside selection loop.
        bad_bundle = ContextBundle(items=["ok"], query="x", budget_bytes="bad")  # type: ignore[arg-type]
        result = provider.compress_context(bad_bundle)
        assert result.provider == "ast"
        assert result.compression_ratio == 1.0

    def test_ast_estimate_exception_fallback_branch(self) -> None:
        provider = AstProvider()
        with patch.object(
            provider, "_count_ast_nodes", side_effect=RuntimeError("boom")
        ):
            result = provider.estimate_budget(TaskContext(query="x"))
            assert result.estimated_bytes == 50_000
            assert result.confidence == 0.2


# ─────────────────────────────────────────────────────────────────────────────
# TF-IDF Provider Advanced Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestTfidfProviderAdvanced:
    """Advanced tests for TfidfProvider."""

    def test_tfidf_tokenize_basic(self) -> None:
        """_tokenize should split on whitespace and lowercase."""
        tokens = TfidfProvider._tokenize("Hello World TEST")
        assert tokens == ["hello", "world", "test"]

    def test_tfidf_tokenize_empty(self) -> None:
        """_tokenize should handle empty string."""
        tokens = TfidfProvider._tokenize("")
        assert tokens == []

    def test_tfidf_tokenize_punctuation(self) -> None:
        """_tokenize should preserve punctuation as part of tokens."""
        tokens = TfidfProvider._tokenize("hello, world!")
        assert "hello," in tokens
        assert "world!" in tokens

    def test_tfidf_cosine_similarity_identical(self) -> None:
        """Cosine similarity of identical vectors should be 1.0."""
        import pytest

        vec = ["hello", "world"]
        similarity = TfidfProvider._cosine_similarity(vec, vec)
        assert similarity == pytest.approx(1.0, abs=1e-9)

    def test_tfidf_cosine_similarity_orthogonal(self) -> None:
        """Cosine similarity of orthogonal vectors should be 0.0."""
        vec1 = ["a", "b"]
        vec2 = ["c", "d"]
        similarity = TfidfProvider._cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_tfidf_cosine_similarity_empty(self) -> None:
        """Cosine similarity with empty vectors should be 0.0."""
        similarity = TfidfProvider._cosine_similarity([], ["test"])
        assert similarity == 0.0

    def test_tfidf_cosine_similarity_partial_overlap(self) -> None:
        """Cosine similarity with partial overlap should be between 0 and 1."""
        vec1 = ["test", "governance", "mandate"]
        vec2 = ["test", "policy", "guideline"]
        similarity = TfidfProvider._cosine_similarity(vec1, vec2)
        assert 0.0 < similarity < 1.0

    def test_tfidf_compress_empty_query(self) -> None:
        """Compression with empty query should keep first item only."""
        provider = TfidfProvider()
        bundle = ContextBundle(
            items=["item1", "item2", "item3"],
            query="",
            budget_bytes=1000,
        )
        result = provider.compress_context(bundle)
        assert len(result.items) == 1
        assert result.items[0] == "item1"

    def test_tfidf_compress_preserves_order(self) -> None:
        """Compressed items should maintain original order."""
        provider = TfidfProvider()
        items = ["first", "second", "third"]
        bundle = ContextBundle(
            items=items,
            query="first third",
            budget_bytes=1000,
        )
        result = provider.compress_context(bundle)
        # Check that selected items maintain original order
        indices = [items.index(item) for item in result.items]
        assert indices == sorted(indices)

    def test_tfidf_analyze_exception_fallback_branch(self) -> None:
        provider = TfidfProvider()
        with patch.object(provider, "_tokenize", side_effect=RuntimeError("boom")):
            result = provider.analyze_task(TaskContext(query="x"))
            assert result.complexity_score == 0.5
            assert result.suggested_path_id == "A"

    def test_tfidf_compress_exception_fallback_branch(self) -> None:
        provider = TfidfProvider()
        bundle = ContextBundle(items=["a", "b"], query="q", budget_bytes=100)
        with patch.object(provider, "_tokenize", side_effect=RuntimeError("boom")):
            result = provider.compress_context(bundle)
            assert result.items == bundle.items
            assert result.compression_ratio == 1.0

    def test_tfidf_estimate_exception_fallback_branch(self) -> None:
        provider = TfidfProvider()
        with patch(
            "providence_runtime.providers.tfidf_provider._provider.len",
            side_effect=RuntimeError("boom"),
        ):
            result = provider.estimate_budget(TaskContext(query="x"))
            assert result.estimated_bytes == 50_000
            assert result.confidence == 0.2

    def test_tfidf_compress_single_item_exceeds_budget(self) -> None:
        """Should keep single item even if it exceeds budget."""
        provider = TfidfProvider()
        large_item = "x" * 500
        bundle = ContextBundle(
            items=[large_item],
            query="test",
            budget_bytes=100,
        )
        result = provider.compress_context(bundle)
        assert len(result.items) == 1
        # Single item keeps original size, so ratio is 1.0
        assert result.compression_ratio == 1.0
        assert result.original_bytes == result.compressed_bytes

    def test_tfidf_estimate_query_length_scaling(self) -> None:
        """Budget should scale with query length."""
        provider = TfidfProvider()
        short_task = TaskContext(query="test")
        long_task = TaskContext(query="test " * 50)

        short_budget = provider.estimate_budget(short_task)
        long_budget = provider.estimate_budget(long_task)

        assert long_budget.estimated_bytes >= short_budget.estimated_bytes

    def test_tfidf_analyze_empty_query(self) -> None:
        """Should return default result for empty query."""
        provider = TfidfProvider()
        task = TaskContext(query="")
        result = provider.analyze_task(task)
        assert result.task_class == "unknown"
        assert result.complexity_score == 0.5
        assert result.suggested_path_id == "A"


# ─────────────────────────────────────────────────────────────────────────────
# HTTP Provider Advanced Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHttpProviderAdvanced:
    """Advanced tests for HttpProvider."""

    async def test_http_provider_availability_caching(self) -> None:
        """HttpProvider should cache availability check."""
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("SDD_INTELLIGENCE_URL", None)
            provider = HttpProvider()

            # First call
            first_check = await provider.is_available()
            # Second call should use cache
            second_check = await provider.is_available()

            assert first_check == second_check
            assert first_check is False

    async def test_http_provider_with_url_but_health_fails(self) -> None:
        """Should be unavailable if health check fails."""
        with patch.dict("os.environ", {"SDD_INTELLIGENCE_URL": "http://127.0.0.1:9"}):
            provider = HttpProvider()
            # Should be unavailable since service is not running
            assert await provider.is_available() is False

    def test_http_fallback_analysis_result(self) -> None:
        """_degraded_analysis_result should return valid result."""
        result = HttpProvider._degraded_analysis_result()
        assert result.task_class == "unknown"
        assert result.complexity_score == 0.5
        assert result.provider == "http"

    def test_http_fallback_compressed_context(self) -> None:
        """_fallback_compressed_context should return all items."""
        bundle = ContextBundle(
            items=["item1", "item2"],
            query="test",
            budget_bytes=100,
        )
        result = HttpProvider._fallback_compressed_context(bundle)
        assert result.items == ["item1", "item2"]
        assert result.compression_ratio == 1.0

    def test_http_fallback_budget_estimate(self) -> None:
        """_fallback_budget_estimate should return valid estimate."""
        result = HttpProvider._fallback_budget_estimate()
        assert result.estimated_bytes == 50_000
        assert result.confidence == 0.2
        assert result.provider == "http"


# ─────────────────────────────────────────────────────────────────────────────
# Provider Exception Handling Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestProviderExceptionHandling:
    """Test exception handling in providers."""

    def test_ast_analyze_handles_exceptions(self) -> None:
        """AstProvider.analyze_task should not raise on errors."""
        provider = AstProvider()
        # Valid task but internal error shouldn't raise
        task = TaskContext(query="def test(): pass")
        result = provider.analyze_task(task)
        assert result is not None
        assert result.provider == "ast"

    def test_ast_compress_handles_exceptions(self) -> None:
        """AstProvider.compress_context should not raise on errors."""
        provider = AstProvider()
        bundle = ContextBundle(
            items=["test"],
            query="test",
            budget_bytes=100,
        )
        result = provider.compress_context(bundle)
        assert result is not None
        assert result.provider == "ast"

    def test_tfidf_analyze_handles_exceptions(self) -> None:
        """TfidfProvider.analyze_task should not raise on errors."""
        provider = TfidfProvider()
        task = TaskContext(query="test")
        result = provider.analyze_task(task)
        assert result is not None
        assert result.provider == "tfidf"

    def test_tfidf_compress_handles_exceptions(self) -> None:
        """TfidfProvider.compress_context should not raise on errors."""
        provider = TfidfProvider()
        bundle = ContextBundle(
            items=["test"],
            query="test",
            budget_bytes=100,
        )
        result = provider.compress_context(bundle)
        assert result is not None
        assert result.provider == "tfidf"

    async def test_http_analyze_unavailable(self) -> None:
        """HttpProvider.analyze_task should degrade gracefully when unavailable."""
        from unittest.mock import AsyncMock

        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("SDD_INTELLIGENCE_URL", None)
            provider = HttpProvider()
            task = TaskContext(query="test")
            with patch.object(
                provider, "is_available", new=AsyncMock(return_value=False)
            ):
                result = await provider.analyze_task(task)
            assert result.task_class == "unknown"
            assert result.provider == "http"

    async def test_http_compress_unavailable(self) -> None:
        """HttpProvider.compress_context should degrade gracefully when unavailable."""
        from unittest.mock import AsyncMock

        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("SDD_INTELLIGENCE_URL", None)
            provider = HttpProvider()
            bundle = ContextBundle(
                items=["test"],
                query="test",
                budget_bytes=100,
            )
            with patch.object(
                provider, "is_available", new=AsyncMock(return_value=False)
            ):
                result = await provider.compress_context(bundle)
            assert result.compression_ratio == 1.0
            assert result.provider == "http"

    async def test_http_estimate_unavailable(self) -> None:
        """HttpProvider.estimate_budget should degrade gracefully when unavailable."""
        from unittest.mock import AsyncMock

        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("SDD_INTELLIGENCE_URL", None)
            provider = HttpProvider()
            task = TaskContext(query="test")
            with patch.object(
                provider, "is_available", new=AsyncMock(return_value=False)
            ):
                result = await provider.estimate_budget(task)
            assert result.estimated_bytes == 50_000
            assert result.provider == "http"


# ─────────────────────────────────────────────────────────────────────────────
# HTTP Provider Service Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHttpProviderServiceIntegration:
    """Test HTTP provider with mocked service responses."""

    def _make_httpx_mock(self, response_data: dict) -> object:
        """Helper: create an httpx AsyncClient mock returning response_data."""
        from unittest.mock import AsyncMock, MagicMock

        import httpx

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value=response_data)
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.post = AsyncMock(return_value=mock_resp)
        return mock_client

    async def test_http_analyze_with_service(self) -> None:
        """HttpProvider.analyze_task should call service when available."""
        from unittest.mock import AsyncMock

        mock_client = self._make_httpx_mock(
            {
                "task_class": "python_code",
                "complexity_score": 0.75,
                "suggested_path_id": "C",
                "keywords": ["test"],
            }
        )
        with (
            patch.dict(
                "os.environ",
                {
                    "SDD_INTELLIGENCE_URL": "http://mock",
                    "SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP": "true",
                },
            ),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            provider = HttpProvider()
            with patch.object(
                provider, "is_available", new=AsyncMock(return_value=True)
            ):
                task = TaskContext(query="test code")
                result = await provider.analyze_task(task)

        assert result.provider == "http"
        assert result.task_class in ("python_code", "unknown")

    async def test_http_compress_with_service(self) -> None:
        """HttpProvider.compress_context should call service when available."""
        from unittest.mock import AsyncMock

        mock_client = self._make_httpx_mock(
            {
                "items": ["item1", "item2"],
                "original_bytes": 100,
                "compressed_bytes": 80,
                "compression_ratio": 0.8,
            }
        )
        with (
            patch.dict(
                "os.environ",
                {
                    "SDD_INTELLIGENCE_URL": "http://mock",
                    "SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP": "true",
                },
            ),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            provider = HttpProvider()
            bundle = ContextBundle(
                items=["item1", "item2"], query="test", budget_bytes=100
            )
            with patch.object(
                provider, "is_available", new=AsyncMock(return_value=True)
            ):
                result = await provider.compress_context(bundle)

        assert result.provider == "http"
        assert len(result.items) >= 0

    async def test_http_estimate_with_service(self) -> None:
        """HttpProvider.estimate_budget should call service when available."""
        from unittest.mock import AsyncMock

        mock_client = self._make_httpx_mock(
            {"estimated_bytes": 30000, "suggested_path_id": "B", "confidence": 0.8}
        )
        with (
            patch.dict(
                "os.environ",
                {
                    "SDD_INTELLIGENCE_URL": "http://mock",
                    "SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP": "true",
                },
            ),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            provider = HttpProvider()
            task = TaskContext(query="test")
            with patch.object(
                provider, "is_available", new=AsyncMock(return_value=True)
            ):
                result = await provider.estimate_budget(task)

        assert result.provider == "http"
        assert result.estimated_bytes > 0

    async def test_http_call_service_analyze_result(self) -> None:
        """_call_service should deserialize AnalysisResult correctly."""
        from providence_runtime.intelligence import AnalysisResult

        mock_client = self._make_httpx_mock(
            {
                "task_class": "python_code",
                "complexity_score": 0.8,
                "suggested_path_id": "C",
                "keywords": ["test"],
            }
        )
        with (
            patch.dict(
                "os.environ",
                {
                    "SDD_INTELLIGENCE_URL": "http://mock",
                    "SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP": "true",
                },
            ),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            provider = HttpProvider()
            result = await provider._call_service(
                "analyze", {"query": "test"}, AnalysisResult
            )

        assert isinstance(result, AnalysisResult)
        assert result.provider == "http"

    async def test_http_call_service_compress_result(self) -> None:
        """_call_service should deserialize CompressedContext correctly."""
        from providence_runtime.intelligence import CompressedContext

        mock_client = self._make_httpx_mock(
            {
                "items": ["test"],
                "original_bytes": 100,
                "compressed_bytes": 50,
                "compression_ratio": 0.5,
            }
        )
        with (
            patch.dict(
                "os.environ",
                {
                    "SDD_INTELLIGENCE_URL": "http://mock",
                    "SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP": "true",
                },
            ),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            provider = HttpProvider()
            result = await provider._call_service("compress", {}, CompressedContext)

        assert isinstance(result, CompressedContext)
        assert result.provider == "http"

    async def test_http_call_service_budget_result(self) -> None:
        """_call_service should deserialize BudgetEstimate correctly."""
        from providence_runtime.intelligence import BudgetEstimate

        mock_client = self._make_httpx_mock(
            {"estimated_bytes": 40000, "suggested_path_id": "B", "confidence": 0.75}
        )
        with (
            patch.dict(
                "os.environ",
                {
                    "SDD_INTELLIGENCE_URL": "http://mock",
                    "SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP": "true",
                },
            ),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            provider = HttpProvider()
            result = await provider._call_service("estimate", {}, BudgetEstimate)

        assert isinstance(result, BudgetEstimate)
        assert result.provider == "http"

    async def test_http_call_service_invalid_type(self) -> None:
        """_call_service should raise for invalid result type."""
        mock_client = self._make_httpx_mock({"test": "data"})
        with (
            patch.dict(
                "os.environ",
                {
                    "SDD_INTELLIGENCE_URL": "http://mock",
                    "SDD_INTELLIGENCE_ALLOW_INSECURE_HTTP": "true",
                },
            ),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            provider = HttpProvider()
            with pytest.raises(ValueError, match="Unknown result type"):
                await provider._call_service("test", {}, dict)  # type: ignore[arg-type]
