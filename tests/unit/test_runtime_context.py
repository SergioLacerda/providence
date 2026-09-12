import pytest
from providence_runtime.artifacts import CompiledArtifact, GovernanceItem
from providence_runtime.context import BudgetBreachError, ContextLoader, ContextRequest


def make_artifact():
    return CompiledArtifact(
        artifact_version="1.0",
        schema_version="1.0",
        fingerprint="abc123",
        generated_at="2026-05-11T00:00:00Z",
        profile="master",
        items=[
            GovernanceItem(
                id="M001", title="Mandate One", item_type="MANDATE", description="desc1"
            ),
            GovernanceItem(
                id="M002", title="Mandate Two", item_type="MANDATE", description="desc2"
            ),
            GovernanceItem(
                id="P001", title="Policy One", item_type="POLICY", description="desc3"
            ),
        ],
    )


def test_budget_breach_raises():
    loader = ContextLoader()
    req = ContextRequest(query="M001", budget_utilization_pct=100.0)
    with pytest.raises(BudgetBreachError):
        loader.load_result(req)


def test_empty_query_returns_fallback():
    loader = ContextLoader()
    req = ContextRequest(query="   ")
    result = loader.load_result(req)
    assert result.items == []
    assert result.source == "fallback"
    assert result.matched == 0
    assert not result.truncated


def test_fallback_without_artifact():
    loader = ContextLoader()
    req = ContextRequest(query="test-query", artifact=None)
    result = loader.load_result(req)
    assert result.items == ["context:test-query"]
    assert result.source == "fallback"
    assert result.matched == 1
    assert not result.truncated
    assert result.bytes_loaded > 0


def test_exact_id_match():
    loader = ContextLoader()
    artifact = make_artifact()
    req = ContextRequest(query="M001", artifact=artifact)
    result = loader.load_result(req)
    assert result.items[0].startswith("M001: Mandate One")
    assert result.source == "artifact"
    assert result.matched == 1
    assert not result.truncated


def test_partial_match_title():
    loader = ContextLoader()
    artifact = make_artifact()
    req = ContextRequest(query="Policy", artifact=artifact)
    result = loader.load_result(req)
    assert any("Policy One" in item for item in result.items)
    assert result.source == "artifact"
    assert result.matched >= 1


def test_type_filter():
    loader = ContextLoader()
    artifact = make_artifact()
    req = ContextRequest(query="Mandate", artifact=artifact, item_types=["MANDATE"])
    result = loader.load_result(req)
    assert all("Mandate" in item for item in result.items)
    assert result.source == "artifact"
    assert result.matched >= 1


def test_type_filter_empty_list_returns_all():
    loader = ContextLoader()
    artifact = make_artifact()
    req = ContextRequest(query="Mandate", artifact=artifact, item_types=[])
    result = loader.load_result(req)
    # Should return all items matching 'Mandate' regardless of type
    assert any("Mandate One" in item for item in result.items)
    assert any("Mandate Two" in item for item in result.items)


def test_query_no_match_returns_empty():
    loader = ContextLoader()
    artifact = make_artifact()
    req = ContextRequest(query="ZZZ", artifact=artifact)
    result = loader.load_result(req)
    assert result.items == []
    assert result.matched == 0
    assert not result.truncated


def test_type_filter_no_match():
    loader = ContextLoader()
    artifact = make_artifact()
    req = ContextRequest(query="Mandate", artifact=artifact, item_types=["NONEXISTENT"])
    result = loader.load_result(req)
    assert result.items == []
    assert result.matched == 0
    assert not result.truncated


def test_max_items_limit():
    loader = ContextLoader()
    artifact = make_artifact()
    req = ContextRequest(query="Mandate", artifact=artifact, max_items=1)
    result = loader.load_result(req)
    assert len(result.items) == 1
    assert result.truncated


def test_load_alias():
    loader = ContextLoader()
    artifact = make_artifact()
    req = ContextRequest(query="M001", artifact=artifact)
    items = loader.load(req)
    assert items[0].startswith("M001: Mandate One")
