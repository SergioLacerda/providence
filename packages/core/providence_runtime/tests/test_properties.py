"""Property-based tests for providence_runtime invariants."""

from __future__ import annotations

import string

import pytest

pytest.importorskip(
    "hypothesis",
    reason="hypothesis not installed — install with: pip install hypothesis",
)

from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402
from providence_runtime.artifacts import CompiledArtifact, GovernanceItem  # noqa: E402


@pytest.mark.slow
class TestCacheKeyProperties:
    """Cache key generation invariants."""

    @given(
        query=st.text(max_size=500),
        max_items=st.integers(min_value=0, max_value=1000),
        item_types=st.lists(st.text(max_size=50), max_size=10),
        budget=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_cache_key_deterministic(
        self, query: str, max_items: int, item_types: list[str], budget: float
    ) -> None:
        """Same inputs always produce the same cache key."""
        from providence_runtime.cache import ContextCache

        k1 = ContextCache._make_key("art-id", query, max_items, item_types, budget)
        k2 = ContextCache._make_key("art-id", query, max_items, item_types, budget)
        assert k1 == k2

    @given(
        query_a=st.text(min_size=1, max_size=50),
        query_b=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_different_queries_produce_different_keys(
        self, query_a: str, query_b: str
    ) -> None:
        """Different queries should produce different cache keys."""
        from providence_runtime.cache import ContextCache

        if query_a == query_b:
            return  # Skip equal inputs
        k1 = ContextCache._make_key("art", query_a, 10, [], 0.0)
        k2 = ContextCache._make_key("art", query_b, 10, [], 0.0)
        assert k1 != k2


@pytest.mark.slow
class TestBudgetProperties:
    """Budget utilization invariants."""

    @given(
        loaded=st.floats(
            min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False
        ),
        budget=st.floats(
            min_value=1.0, max_value=1e9, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_budget_utilization_non_negative(
        self, loaded: float, budget: float
    ) -> None:
        """Budget utilization is always non-negative."""
        utilization = (loaded / budget) * 100.0
        assert utilization >= 0.0

    @given(
        loaded=st.floats(
            min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        budget=st.floats(
            min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_utilization_exceeds_100_when_overloaded(
        self, loaded: float, budget: float
    ) -> None:
        """Utilization exceeds 100% when loaded > budget."""
        if loaded <= budget:
            return
        utilization = (loaded / budget) * 100.0
        assert utilization > 100.0


@pytest.mark.slow
class TestItemTypeFilterProperties:
    """GovernanceItem type filter invariants."""

    @given(
        item_type=st.text(alphabet=string.ascii_letters, min_size=1, max_size=20),
    )
    @settings(max_examples=100)
    def test_item_type_filter_case_insensitive(self, item_type: str) -> None:
        """items_by_type is case-insensitive."""
        item = GovernanceItem(
            id="M001",
            title="Test Mandate",
            item_type="MANDATE",
            description="",
            rationale="",
            summary_minimal="",
            summary_runtime="",
        )
        artifact = CompiledArtifact(
            artifact_version="3.0",
            schema_version="3.0",
            fingerprint="fp1",
            generated_at="2026-01-01T00:00:00Z",
            profile="master",
            items=[item],
        )
        assert artifact.items_by_type(item_type.upper()) == artifact.items_by_type(
            item_type.lower()
        )

    @given(
        item_type=st.text(alphabet=string.ascii_letters, min_size=1, max_size=20),
    )
    @settings(max_examples=50)
    def test_items_by_type_only_returns_matching(self, item_type: str) -> None:
        """items_by_type only returns items whose type matches."""
        item = GovernanceItem(
            id="M001",
            title="Test",
            item_type="MANDATE",
            description="",
            rationale="",
            summary_minimal="",
            summary_runtime="",
        )
        artifact = CompiledArtifact(
            artifact_version="3.0",
            schema_version="3.0",
            fingerprint="fp1",
            generated_at="2026-01-01T00:00:00Z",
            profile="master",
            items=[item],
        )
        result = artifact.items_by_type(item_type)
        for r in result:
            assert r.item_type.upper() == item_type.upper()
