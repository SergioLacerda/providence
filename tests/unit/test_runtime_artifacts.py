import json

import pytest
from providence_runtime.artifacts import CompiledArtifact, GovernanceItem


def make_items():
    return [
        GovernanceItem(
            id="M001",
            title="Mandate One",
            item_type="MANDATE",
            description="desc1",
            rationale="r1",
        ),
        GovernanceItem(
            id="P001",
            title="Policy One",
            item_type="POLICY",
            description="desc2",
            rationale="r2",
        ),
    ]


def test_items_by_type_case_insensitive():
    artifact = CompiledArtifact(
        artifact_version="1.0",
        schema_version="1.0",
        fingerprint="abc",
        generated_at="now",
        profile="master",
        items=make_items(),
    )
    mandates = artifact.items_by_type("mandate")
    assert len(mandates) == 1
    assert mandates[0].id == "M001"
    policies = artifact.items_by_type("POLICY")
    assert len(policies) == 1
    assert policies[0].id == "P001"
    none = artifact.items_by_type("GUIDELINE")
    assert none == []


def test_find_by_id_case_insensitive():
    artifact = CompiledArtifact(
        artifact_version="1.0",
        schema_version="1.0",
        fingerprint="abc",
        generated_at="now",
        profile="master",
        items=make_items(),
    )
    found = artifact.find_by_id("m001")
    assert found is not None
    assert found.title == "Mandate One"
    notfound = artifact.find_by_id("X999")
    assert notfound is None


def test_from_governance_json(tmp_path):
    items_data = {
        "version": "2.0",
        "fingerprint": "fp123",
        "items": [
            {
                "id": "M001",
                "title": "Mandate One",
                "metadata": {
                    "type": "MANDATE",
                    "description": "desc1",
                    "rationale": "r1",
                },
            },
            {
                "id": "P001",
                "title": "Policy One",
                "metadata": {
                    "type": "POLICY",
                    "description": "desc2",
                    "rationale": "r2",
                },
            },
        ],
    }
    meta_data = {"generated_at": "2026-05-11T00:00:00Z", "version": "2.0"}
    items_path = tmp_path / "governance-core.json"
    metadata_path = tmp_path / "metadata-core.json"
    items_path.write_text(json.dumps(items_data), encoding="utf-8")
    metadata_path.write_text(json.dumps(meta_data), encoding="utf-8")
    artifact = CompiledArtifact.from_governance_json(
        items_path, metadata_path, profile="client"
    )
    assert artifact.artifact_version == "2.0"
    assert artifact.schema_version == "2.0"
    assert artifact.fingerprint == "fp123"
    assert artifact.generated_at == "2026-05-11T00:00:00Z"
    assert artifact.profile == "client"
    assert len(artifact.items) == 2
    assert artifact.items[0].id == "M001"
    assert artifact.items[1].item_type == "POLICY"


def test_from_sdd_compiled_dir(tmp_path):
    # Should raise if missing file
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        CompiledArtifact.from_sdd_compiled_dir(compiled_dir)
    # Now create files
    items_data = {"version": "1.0", "fingerprint": "fp", "items": []}
    meta_data = {"generated_at": "now", "version": "1.0"}
    (compiled_dir / "governance-core.json").write_text(
        json.dumps(items_data), encoding="utf-8"
    )
    (compiled_dir / "metadata-core.json").write_text(
        json.dumps(meta_data), encoding="utf-8"
    )
    artifact = CompiledArtifact.from_sdd_compiled_dir(compiled_dir)
    assert artifact.artifact_version == "1.0"
    assert artifact.generated_at == "now"
    assert artifact.items == []
