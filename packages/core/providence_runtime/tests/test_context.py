"""Tests for context loading engine."""

from __future__ import annotations

import pytest
from providence_runtime.artifacts import CompiledArtifact, GovernanceItem
from providence_runtime.context import (
    BudgetBreachError,
    ContextLoader,
    ContextRequest,
    ContextResult,
)

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_items() -> list[GovernanceItem]:
    """Create sample governance items for testing."""
    return [
        GovernanceItem(
            id="M001",
            item_type="MANDATE",
            title="Clean Architecture",
            description="Enforce layered architecture",
        ),
        GovernanceItem(
            id="M002",
            item_type="MANDATE",
            title="Test-Driven Development",
            description="Write tests first",
        ),
        GovernanceItem(
            id="P001",
            item_type="POLICY",
            title="Code Review",
            description="All changes require review",
        ),
    ]


@pytest.fixture
def sample_artifact(sample_items) -> CompiledArtifact:
    """Create a sample compiled artifact."""
    return CompiledArtifact(
        artifact_version="1.0",
        schema_version="3.0",
        fingerprint="test-fp",
        generated_at="2026-05-12T00:00:00Z",
        profile="master",
        items=sample_items,
    )


# ─────────────────────────────────────────────────────────────────────────────
# BudgetBreachError Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBudgetBreachError:
    """Test BudgetBreachError initialization and messages."""

    def test_init_without_path(self) -> None:
        """BudgetBreachError should initialize without PATH."""
        err = BudgetBreachError(utilization_pct=150.0)
        assert err.utilization_pct == 150.0
        assert err.path_id == ""
        assert "150.0%" in str(err)
        assert "BREACH" in str(err)

    def test_init_with_path(self) -> None:
        """BudgetBreachError should include PATH in message."""
        err = BudgetBreachError(utilization_pct=120.0, path_id="C")
        assert err.path_id == "C"
        assert "PATH C" in str(err)


# ─────────────────────────────────────────────────────────────────────────────
# ContextRequest & ContextResult Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestContextRequest:
    """Test ContextRequest dataclass."""

    def test_default_initialization(self) -> None:
        """ContextRequest should initialize with defaults."""
        req = ContextRequest(query="test")
        assert req.query == "test"
        assert req.max_items == 5
        assert req.artifact is None
        assert req.item_types == []
        assert req.budget_utilization_pct is None
        assert req.prefer_full_summary is False

    def test_with_budget_utilization(self) -> None:
        """ContextRequest should accept budget utilization."""
        req = ContextRequest(query="test", budget_utilization_pct=75.0)
        assert req.budget_utilization_pct == 75.0


class TestContextResult:
    """Test ContextResult dataclass."""

    def test_initialization(self) -> None:
        """ContextResult should initialize correctly."""
        result = ContextResult(
            items=["M001: Test", "M002: Test"],
            source="artifact",
            matched=2,
            truncated=False,
            bytes_loaded=100,
        )
        assert result.items == ["M001: Test", "M002: Test"]
        assert result.source == "artifact"
        assert result.matched == 2
        assert result.truncated is False
        assert result.bytes_loaded == 100
        assert result.compression_ratio is None


# ─────────────────────────────────────────────────────────────────────────────
# ContextLoader Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestContextLoaderInit:
    """Test ContextLoader initialization."""

    def test_init_without_registry(self) -> None:
        """ContextLoader should initialize with default registry."""
        loader = ContextLoader()
        assert loader.registry is not None

    def test_init_with_registry(self) -> None:
        """ContextLoader should accept custom registry."""
        from unittest.mock import MagicMock

        mock_registry = MagicMock()
        loader = ContextLoader(registry=mock_registry)
        assert loader.registry is mock_registry

    def test_default_registry_chain_is_ast_then_tfidf_no_http(self) -> None:
        """CTX-01 regression: documentation used to claim `HttpProvider` was
        first in the default chain. `HttpProvider` is async-only and
        incompatible with this synchronous `ProviderRegistry` — the actual
        default is `[AstProvider, TfidfProvider]`, with the registry's own
        built-in `LocalIntelligenceProvider` as its always-available
        fallback when neither is available.
        `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` CTX-01.
        """
        from providence_runtime.providers import AstProvider, TfidfProvider

        loader = ContextLoader()
        providers = loader.registry._providers

        assert [type(p) for p in providers] == [AstProvider, TfidfProvider]
        assert not any(type(p).__name__ == "HttpProvider" for p in providers)


class TestContextLoaderLoad:
    """Test ContextLoader.load() method."""

    def test_load_returns_list(self, sample_artifact) -> None:
        """load() should return list of strings."""
        loader = ContextLoader()
        request = ContextRequest(query="M001", artifact=sample_artifact, max_items=5)
        result = loader.load(request)
        assert isinstance(result, list)
        assert all(isinstance(item, str) for item in result)

    def test_load_delegates_to_load_result(self, sample_artifact) -> None:
        """load() should delegate to load_result()."""
        loader = ContextLoader()
        request = ContextRequest(query="M001", artifact=sample_artifact, max_items=5)
        items = loader.load(request)
        result = loader.load_result(request)
        assert items == result.items


class TestContextLoaderLoadResult:
    """Test ContextLoader.load_result() method."""

    @pytest.fixture(autouse=True)
    def _clear_cache(self) -> None:
        """Clear the global context cache before each test."""
        ContextLoader._cache.clear()
        yield
        ContextLoader._cache.clear()

    def test_breach_raises_error(self) -> None:
        """load_result() should raise BudgetBreachError when utilization ≥ 100%."""
        loader = ContextLoader()
        request = ContextRequest(
            query="test",
            budget_utilization_pct=100.0,
        )
        with pytest.raises(BudgetBreachError) as exc_info:
            loader.load_result(request)
        assert exc_info.value.utilization_pct == 100.0

    def test_breach_with_150_percent(self) -> None:
        """load_result() should raise BudgetBreachError at 150%."""
        loader = ContextLoader()
        request = ContextRequest(
            query="test",
            budget_utilization_pct=150.0,
        )
        with pytest.raises(BudgetBreachError):
            loader.load_result(request)

    def test_empty_query_returns_fallback(self) -> None:
        """load_result() should return empty fallback for empty query."""
        loader = ContextLoader()
        request = ContextRequest(query="")
        result = loader.load_result(request)
        assert result.items == []
        assert result.source == "fallback"
        assert result.matched == 0
        assert result.truncated is False

    def test_whitespace_query_returns_fallback(self) -> None:
        """load_result() should return empty fallback for whitespace query."""
        loader = ContextLoader()
        request = ContextRequest(query="   ")
        result = loader.load_result(request)
        assert result.items == []
        assert result.source == "fallback"

    def test_no_artifact_returns_fallback(self) -> None:
        """load_result() should return deterministic fallback when no artifact."""
        loader = ContextLoader()
        request = ContextRequest(query="test query")
        result = loader.load_result(request)
        assert result.source == "fallback"
        assert result.items == ["context:test query"]
        assert result.matched == 1
        assert result.truncated is False
        assert result.bytes_loaded > 0

    def test_loads_from_artifact(self, sample_artifact) -> None:
        """load_result() should load items from artifact."""
        loader = ContextLoader()
        request = ContextRequest(
            query="M001",
            artifact=sample_artifact,
            max_items=5,
        )
        result = loader.load_result(request)
        assert result.source == "artifact"
        assert result.matched > 0
        assert "M001" in result.items[0]

    def test_respects_max_items_limit(self, sample_artifact) -> None:
        """load_result() should respect max_items limit."""
        loader = ContextLoader()
        request = ContextRequest(
            query="M",  # Matches both M001 and M002
            artifact=sample_artifact,
            max_items=1,
        )
        result = loader.load_result(request)
        assert len(result.items) == 1
        assert result.truncated is True

    def test_truncated_flag_when_exceeded(self, sample_artifact) -> None:
        """load_result() should set truncated=True when items exceed limit."""
        loader = ContextLoader()
        request = ContextRequest(
            query="M",  # Matches both M001 and M002 (multiple MANDATEs)
            artifact=sample_artifact,
            max_items=1,
            item_types=["MANDATE"],
        )
        result = loader.load_result(request)
        assert result.truncated is True

    def test_not_truncated_when_within_limit(self, sample_artifact) -> None:
        """load_result() should set truncated=False when within limit."""
        loader = ContextLoader()
        request = ContextRequest(
            query="M001",
            artifact=sample_artifact,
            max_items=10,
        )
        result = loader.load_result(request)
        assert result.truncated is False

    def test_yellow_zone_compression_attempt(self, sample_artifact) -> None:
        """load_result() should attempt compression in YELLOW zone (70-90%)."""
        loader = ContextLoader()
        request = ContextRequest(
            query="M",
            artifact=sample_artifact,
            max_items=10,
            budget_utilization_pct=75.0,  # YELLOW zone
        )
        result = loader.load_result(request)
        # Should attempt compression; may or may not apply depending on provider
        assert result.source == "artifact"

    def test_no_compression_in_green_zone(self, sample_artifact) -> None:
        """load_result() should not attempt compression in GREEN zone (< 70%)."""
        loader = ContextLoader()
        request = ContextRequest(
            query="M",
            artifact=sample_artifact,
            max_items=10,
            budget_utilization_pct=50.0,  # GREEN zone
        )
        result = loader.load_result(request)
        assert result.compression_ratio is None

    def test_no_compression_at_breach(self, sample_artifact) -> None:
        """load_result() should not reach compression logic at BREACH."""
        loader = ContextLoader()
        request = ContextRequest(
            query="M",
            artifact=sample_artifact,
            budget_utilization_pct=100.0,  # BREACH
        )
        with pytest.raises(BudgetBreachError):
            loader.load_result(request)


# ─────────────────────────────────────────────────────────────────────────────
# _match_items Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestContextLoaderMatchItems:
    """Test ContextLoader._match_items() helper."""

    def test_exact_id_match(self, sample_items) -> None:
        """_match_items should find exact ID match."""
        artifact = CompiledArtifact(
            artifact_version="1.0",
            schema_version="3.0",
            fingerprint="test-fp",
            generated_at="2026-05-12T00:00:00Z",
            profile="master",
            items=sample_items,
        )
        matched = ContextLoader._match_items(artifact, "M001", [])
        assert len(matched) == 1
        assert matched[0].id == "M001"

    def test_case_insensitive_id_match(self, sample_items) -> None:
        """_match_items should match IDs case-insensitively."""
        artifact = CompiledArtifact(
            artifact_version="1.0",
            schema_version="3.0",
            fingerprint="test-fp",
            generated_at="2026-05-12T00:00:00Z",
            profile="master",
            items=sample_items,
        )
        matched = ContextLoader._match_items(artifact, "m001", [])
        assert len(matched) == 1
        assert matched[0].id == "M001"

    def test_partial_id_match(self, sample_items) -> None:
        """_match_items should find partial ID matches."""
        artifact = CompiledArtifact(
            artifact_version="1.0",
            schema_version="3.0",
            fingerprint="test-fp",
            generated_at="2026-05-12T00:00:00Z",
            profile="master",
            items=sample_items,
        )
        matched = ContextLoader._match_items(artifact, "M00", [])
        assert len(matched) >= 1
        assert any("M001" in str(m.id) or "M002" in str(m.id) for m in matched)

    def test_title_match(self, sample_items) -> None:
        """_match_items should match on title."""
        artifact = CompiledArtifact(
            artifact_version="1.0",
            schema_version="3.0",
            fingerprint="test-fp",
            generated_at="2026-05-12T00:00:00Z",
            profile="master",
            items=sample_items,
        )
        matched = ContextLoader._match_items(artifact, "Clean", [])
        assert len(matched) >= 1
        assert "Clean Architecture" in [m.title for m in matched]

    def test_description_match(self, sample_items) -> None:
        """_match_items should match on description."""
        artifact = CompiledArtifact(
            artifact_version="1.0",
            schema_version="3.0",
            fingerprint="test-fp",
            generated_at="2026-05-12T00:00:00Z",
            profile="master",
            items=sample_items,
        )
        matched = ContextLoader._match_items(artifact, "layered", [])
        assert len(matched) >= 1

    def test_type_filter(self, sample_items) -> None:
        """_match_items should filter by type."""
        artifact = CompiledArtifact(
            artifact_version="1.0",
            schema_version="3.0",
            fingerprint="test-fp",
            generated_at="2026-05-12T00:00:00Z",
            profile="master",
            items=sample_items,
        )
        matched = ContextLoader._match_items(artifact, "M", ["MANDATE"])
        # All matches should be MANDATEs
        assert all(m.item_type.upper() == "MANDATE" for m in matched)

    def test_type_filter_case_insensitive(self, sample_items) -> None:
        """_match_items should filter by type case-insensitively."""
        artifact = CompiledArtifact(
            artifact_version="1.0",
            schema_version="3.0",
            fingerprint="test-fp",
            generated_at="2026-05-12T00:00:00Z",
            profile="master",
            items=sample_items,
        )
        matched = ContextLoader._match_items(artifact, "M", ["mandate"])
        assert all(m.item_type.upper() == "MANDATE" for m in matched)

    def test_no_matches(self, sample_items) -> None:
        """_match_items should return empty list when no match."""
        artifact = CompiledArtifact(
            artifact_version="1.0",
            schema_version="3.0",
            fingerprint="test-fp",
            generated_at="2026-05-12T00:00:00Z",
            profile="master",
            items=sample_items,
        )
        matched = ContextLoader._match_items(artifact, "NONEXISTENT", [])
        assert matched == []

    def test_exact_match_takes_priority(self, sample_items) -> None:
        """_match_items should return exact match over partial matches."""
        artifact = CompiledArtifact(
            artifact_version="1.0",
            schema_version="3.0",
            fingerprint="test-fp",
            generated_at="2026-05-12T00:00:00Z",
            profile="master",
            items=sample_items,
        )
        matched = ContextLoader._match_items(artifact, "M001", [])
        # Exact match should be first (and only, since M001 doesn't appear elsewhere)
        assert matched[0].id == "M001"


# ---------------------------------------------------------------------------
# Compression error handling (YELLOW zone)
# ---------------------------------------------------------------------------


class TestContextLoaderCompressionErrors:
    @pytest.fixture(autouse=True)
    def _clear_cache(self) -> None:
        """Clear the global context cache before each test."""
        ContextLoader._cache.clear()
        yield
        ContextLoader._cache.clear()

    def test_compression_failure_logged_not_raised(self, sample_artifact) -> None:
        """load_result() should catch and log compression exceptions gracefully."""
        from unittest.mock import MagicMock

        loader = ContextLoader()
        # Mock registry to raise during compression
        mock_registry = MagicMock()
        mock_registry.compress_context.side_effect = RuntimeError("compression failed")
        loader._registry = mock_registry

        request = ContextRequest(
            query="M",
            artifact=sample_artifact,
            max_items=10,
            budget_utilization_pct=75.0,  # YELLOW zone
        )

        # Should not raise, but return result anyway
        result = loader.load_result(request)
        assert result.source == "artifact"
        assert result.compression_ratio is None  # No compression applied
        assert result.matched > 0  # But items were still loaded

    def test_compression_attempted_and_failed_sets_structured_fields(
        self, sample_artifact
    ) -> None:
        """Fase 4: a failed compression attempt reports attempted=True and the
        raised exception's class name as failure_code, not just a silent
        compression_ratio=None."""
        from unittest.mock import MagicMock

        loader = ContextLoader()
        mock_registry = MagicMock()
        mock_registry.compress_context.side_effect = RuntimeError("compression failed")
        loader._registry = mock_registry

        request = ContextRequest(
            query="M",
            artifact=sample_artifact,
            max_items=10,
            budget_utilization_pct=75.0,  # YELLOW zone
        )
        result = loader.load_result(request)
        assert result.compression_attempted is True
        assert result.compression_failure_code == "RuntimeError"

    def test_compression_attempted_and_succeeded_sets_structured_fields(
        self, sample_artifact
    ) -> None:
        """Fase 4: a successful compression attempt reports attempted=True and
        no failure_code."""
        from unittest.mock import MagicMock

        from providence_runtime.intelligence import CompressedContext

        loader = ContextLoader()
        mock_registry = MagicMock()
        mock_registry.compress_context.return_value = CompressedContext(
            items=["compressed"],
            original_bytes=100,
            compressed_bytes=10,
            compression_ratio=0.1,
            provider="mock",
        )
        loader._registry = mock_registry

        request = ContextRequest(
            query="M",
            artifact=sample_artifact,
            max_items=10,
            budget_utilization_pct=75.0,  # YELLOW zone
        )
        result = loader.load_result(request)
        assert result.compression_attempted is True
        assert result.compression_failure_code is None
        assert result.compression_ratio == 0.1

    def test_compression_not_attempted_in_green_zone_leaves_defaults(
        self, sample_artifact
    ) -> None:
        """Fase 4: outside the YELLOW/RED zone, the structured fields stay at
        their defaults — compression was never attempted, not silently failed."""
        loader = ContextLoader()

        request = ContextRequest(
            query="M",
            artifact=sample_artifact,
            max_items=10,
            budget_utilization_pct=50.0,  # GREEN zone
        )
        result = loader.load_result(request)
        assert result.compression_attempted is False
        assert result.compression_failure_code is None

    def test_compression_failure_logs_at_warning_not_debug(
        self, sample_artifact, caplog
    ) -> None:
        """CTX-04 regression: a genuine compression exception must be
        visible at WARNING (DEBUG is invisible in normal operation) — the
        loader still fails open (no raise), but the failure itself must not
        be silent.
        `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` CTX-04.
        """
        from unittest.mock import MagicMock

        loader = ContextLoader()
        mock_registry = MagicMock()
        mock_registry.compress_context.side_effect = RuntimeError("boom")
        loader._registry = mock_registry

        request = ContextRequest(
            query="M",
            artifact=sample_artifact,
            max_items=10,
            budget_utilization_pct=95.0,  # RED zone — also attempts compression
        )

        with caplog.at_level("WARNING", logger="providence_runtime.context._loader"):
            loader.load_result(request)

        assert any("Compression failed" in record.message for record in caplog.records)

    def test_compression_failure_propagates_to_economy_compression_skip_event(
        self, sample_artifact
    ) -> None:
        """CTX-04: a compression failure's `compression_ratio=None` at
        YELLOW/RED utilization is exactly the condition
        `TelemetrySink._maybe_emit_zone_event` uses to auto-emit
        `economy.compression.skip` — verifying the existing downstream
        signal actually fires, closing the loop from "silent failure" to an
        explicit, non-silent telemetry event."""
        from unittest.mock import MagicMock

        from providence_runtime import RuntimeEvent, TelemetrySink

        loader = ContextLoader()
        mock_registry = MagicMock()
        mock_registry.compress_context.side_effect = RuntimeError("boom")
        loader._registry = mock_registry

        request = ContextRequest(
            query="M",
            artifact=sample_artifact,
            max_items=10,
            budget_utilization_pct=75.0,
        )
        result = loader.load_result(request)
        assert result.compression_ratio is None

        sink = TelemetrySink()
        sink.emit(
            RuntimeEvent(
                event="governance.ask",
                command="ask",
                status="ok",
                trace_id="t1",
                budget_utilization_pct=request.budget_utilization_pct,
                compression_ratio=result.compression_ratio,
            )
        )
        events = [e.event for e in sink.list_events()]
        assert "economy.compression.skip" in events


# ---------------------------------------------------------------------------
# _render_item progressive disclosure
# ---------------------------------------------------------------------------


class TestContextLoaderRenderItem:
    def test_render_item_uses_summary_minimal_in_red_zone(self) -> None:
        item = GovernanceItem(
            id="M001",
            item_type="MANDATE",
            title="Clean Architecture",
            summary_minimal="Minimal summary",
            summary_runtime="Runtime summary",
            summary_full="Full summary",
            criticality="high",
        )
        rendered = ContextLoader._render_item(item, budget_utilization_pct=95.0)
        assert rendered == "Minimal summary"

    def test_render_item_uses_summary_runtime_in_yellow_zone(self) -> None:
        item = GovernanceItem(
            id="M001",
            item_type="MANDATE",
            title="Clean Architecture",
            summary_minimal="Minimal summary",
            summary_runtime="Runtime summary",
            summary_full="Full summary",
            criticality="high",
        )
        rendered = ContextLoader._render_item(item, budget_utilization_pct=80.0)
        assert rendered == "Runtime summary"

    def test_render_item_green_zone_keeps_default_rendering(self) -> None:
        item = GovernanceItem(
            id="M001",
            item_type="MANDATE",
            title="Clean Architecture",
            summary_minimal="Minimal summary",
            summary_runtime="Runtime summary",
            summary_full="Full summary",
            criticality="high",
        )
        rendered = ContextLoader._render_item(item, budget_utilization_pct=50.0)
        assert rendered == "M001: Clean Architecture"

    def test_render_item_green_zone_can_prefer_summary_full(self) -> None:
        item = GovernanceItem(
            id="M001",
            item_type="MANDATE",
            title="Clean Architecture",
            summary_minimal="Minimal summary",
            summary_runtime="Runtime summary",
            summary_full="Full summary",
            criticality="high",
        )
        rendered = ContextLoader._render_item(
            item,
            budget_utilization_pct=50.0,
            prefer_full_summary=True,
        )
        assert rendered == "Full summary"

    def test_load_result_green_zone_prefer_summary_full(self, sample_artifact) -> None:
        loader = ContextLoader()
        request = ContextRequest(
            query="M001",
            artifact=sample_artifact,
            max_items=5,
            budget_utilization_pct=50.0,
            prefer_full_summary=True,
        )
        # Ensure fixture item has summary_full to exercise rendering path.
        sample_artifact.items[0].summary_full = "Long form governance summary"
        result = loader.load_result(request)
        assert result.items
        assert result.items[0] == "Long form governance summary"
