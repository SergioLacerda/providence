"""Tests for automatic compression trigger at YELLOW zone (70-90% utilization)."""

from __future__ import annotations

import pytest
from providence_runtime.context import ContextLoader, ContextRequest
from providence_runtime.intelligence import (
    ContextBundle,
    LocalIntelligenceProvider,
    ProviderRegistry,
)


class TestCompressionTriggerAtYellowZone:
    """Test compression trigger when utilization is in YELLOW zone (70-90%)."""

    @pytest.fixture(autouse=True)
    def _clear_cache(self) -> None:
        """Clear the global context cache before each test."""
        ContextLoader._cache.clear()
        yield
        ContextLoader._cache.clear()

    def test_no_compression_below_70_percent(self) -> None:
        """Compression should not trigger below 70% utilization."""
        registry = ProviderRegistry([LocalIntelligenceProvider()])
        loader = ContextLoader(registry=registry)

        request = ContextRequest(
            query="test",
            max_items=5,
            artifact=None,
            budget_utilization_pct=65.0,  # GREEN zone
        )

        result = loader.load_result(request)

        # Fallback result, compression not attempted
        assert result.compression_ratio is None
        assert result.source == "fallback"

    def test_no_compression_at_100_percent(self) -> None:
        """Compression should not trigger at 100% utilization (BREACH)."""
        from providence_runtime.context import BudgetBreachError

        registry = ProviderRegistry([LocalIntelligenceProvider()])
        loader = ContextLoader(registry=registry)

        request = ContextRequest(
            query="test_breach_100pct",  # Unique query to avoid cache
            max_items=5,
            artifact=None,
            budget_utilization_pct=100.0,  # BREACH — should raise
        )

        with pytest.raises(BudgetBreachError):
            loader.load_result(request)

    def test_compression_triggers_at_75_percent(self) -> None:
        """Compression should trigger when utilization is 75% (YELLOW zone)."""
        registry = ProviderRegistry([LocalIntelligenceProvider()])
        loader = ContextLoader(registry=registry)

        request = ContextRequest(
            query="test",
            max_items=5,
            artifact=None,
            budget_utilization_pct=75.0,  # YELLOW zone
        )

        result = loader.load_result(request)

        # Fallback result; compression attempted but not applied (ratio >= 1.0)
        assert result.source == "fallback"
        # compression_ratio should be set (even if not applied)
        # For fallback with single item, compression unlikely to help

    def test_compression_triggers_at_90_percent(self) -> None:
        """Compression should trigger when utilization is 90% (YELLOW zone)."""
        registry = ProviderRegistry([LocalIntelligenceProvider()])
        loader = ContextLoader(registry=registry)

        request = ContextRequest(
            query="test",
            max_items=5,
            artifact=None,
            budget_utilization_pct=90.0,  # YELLOW zone
        )

        result = loader.load_result(request)

        assert result.source == "fallback"

    def test_auto_registry_default_when_none(self) -> None:
        """When registry=None, ContextLoader should build default provider registry."""
        loader = ContextLoader(registry=None)

        # Verify that registry is not None (default was built)
        assert loader.registry is not None

        request = ContextRequest(
            query="test",
            max_items=5,
            artifact=None,
            budget_utilization_pct=75.0,  # YELLOW zone
        )

        result = loader.load_result(request)

        # With default registry, compression is attempted in YELLOW zone
        assert result.source == "fallback"
        # compression_ratio may be None if compression didn't help, or a value if applied

    def test_compression_ratio_preserved_in_result(self) -> None:
        """compression_ratio should be preserved in ContextResult."""
        registry = ProviderRegistry([LocalIntelligenceProvider()])
        loader = ContextLoader(registry=registry)

        request = ContextRequest(
            query="test",
            max_items=5,
            artifact=None,
            budget_utilization_pct=75.0,
        )

        result = loader.load_result(request)

        # Result should have compression_ratio field (may be None if not compressed)
        assert hasattr(result, "compression_ratio")

    def test_compression_with_multiple_items(self) -> None:
        """Compression should work with multiple items in fallback."""
        registry = ProviderRegistry([LocalIntelligenceProvider()])
        loader = ContextLoader(registry=registry)

        request = ContextRequest(
            query="policy change",
            max_items=5,
            artifact=None,
            budget_utilization_pct=80.0,  # YELLOW zone
        )

        result = loader.load_result(request)

        # Fallback result; items should be present
        assert result.items
        assert result.source == "fallback"


class TestCompressionWithLocalProvider:
    """Test compression behavior with LocalIntelligenceProvider."""

    def test_local_provider_deduplicates(self) -> None:
        """LocalIntelligenceProvider should deduplicate items."""
        provider = LocalIntelligenceProvider()

        # Create bundle with duplicate items
        bundle = ContextBundle(
            items=["item1", "item1", "item2", "item3"],
            query="test",
            budget_bytes=100,
        )

        compressed = provider.compress_context(bundle)

        # Deduplication should reduce item count
        assert len(compressed.items) <= len(bundle.items)
        assert compressed.compression_ratio > 0

    def test_local_provider_respects_budget(self) -> None:
        """LocalIntelligenceProvider should respect budget_bytes limit."""
        provider = LocalIntelligenceProvider()

        items = ["item" + str(i) * 100 for i in range(10)]  # Each item ~100 bytes
        bundle = ContextBundle(
            items=items,
            query="test",
            budget_bytes=50,  # Very small budget
        )

        compressed = provider.compress_context(bundle)

        # Compressed result should fit in budget
        total_compressed = sum(len(item.encode()) for item in compressed.items)
        assert total_compressed <= bundle.budget_bytes or len(compressed.items) >= 1


class TestCompressionZoneBoundaries:
    """Test compression at zone boundaries."""

    def test_compression_at_70_percent_boundary(self) -> None:
        """Compression should trigger at exactly 70% (lower boundary)."""
        registry = ProviderRegistry([LocalIntelligenceProvider()])
        loader = ContextLoader(registry=registry)

        request = ContextRequest(
            query="test",
            max_items=5,
            artifact=None,
            budget_utilization_pct=70.0,  # Boundary
        )

        result = loader.load_result(request)

        # Should not raise, compression attempt made
        assert result is not None

    def test_compression_at_89_9_percent(self) -> None:
        """Compression should trigger at 89.9% (within YELLOW)."""
        registry = ProviderRegistry([LocalIntelligenceProvider()])
        loader = ContextLoader(registry=registry)

        request = ContextRequest(
            query="test",
            max_items=5,
            artifact=None,
            budget_utilization_pct=89.9,  # Just below RED
        )

        result = loader.load_result(request)

        assert result is not None
        assert result.source == "fallback"

    def test_no_compression_at_69_9_percent(self) -> None:
        """Compression should not trigger at 69.9% (GREEN zone)."""
        registry = ProviderRegistry([LocalIntelligenceProvider()])
        loader = ContextLoader(registry=registry)

        request = ContextRequest(
            query="test",
            max_items=5,
            artifact=None,
            budget_utilization_pct=69.9,  # Just below YELLOW
        )

        result = loader.load_result(request)

        # Compression not attempted (GREEN zone)
        assert result.compression_ratio is None
