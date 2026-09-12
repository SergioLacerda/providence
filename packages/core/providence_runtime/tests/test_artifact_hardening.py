import json
from pathlib import Path

from providence_runtime.artifacts import CompiledArtifact
from providence_runtime.injection import GovernanceInjector


def test_warn_invalid_sig_sets_auth_degraded(tmp_path: Path, monkeypatch):
    # Setup artifact without signature
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir()
    artifact_path = compiled_dir / "governance-core.json"
    artifact_path.write_text(
        json.dumps({"fingerprint": "test-fp", "schema_version": "1.0", "items": []}),
        encoding="utf-8",
    )

    # Enable warn mode
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "warn")

    # Act
    result = CompiledArtifact.from_sdd_compiled_dir_with_auth(compiled_dir)

    # Assert
    assert result.auth_state == "degraded"
    assert result.artifact.fingerprint == "test-fp"


def test_runtime_loader_propagates_auth_state(tmp_path: Path, monkeypatch):
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir()
    artifact_path = compiled_dir / "governance-core.json"
    artifact_path.write_text(
        json.dumps({"fingerprint": "test-fp", "schema_version": "1.0", "items": []}),
        encoding="utf-8",
    )

    monkeypatch.setenv("SDD_SIGNATURE_MODE", "warn")

    injector = GovernanceInjector()
    result = injector.inject_from_path(compiled_dir)

    assert result.auth_state == "degraded"
    assert result.artifact_fingerprint == "test-fp"
