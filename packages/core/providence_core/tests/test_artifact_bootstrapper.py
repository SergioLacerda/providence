"""Tests for `providence_core.artifact_bootstrapper`."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from providence_core.artifact_bootstrapper import (
    GOVERNANCE_ARTIFACTS,
    ArtifactBootstrapper,
)


def _metadata_source_factory(compiled_dir: Path):
    def _metadata_source(filename: str) -> Path:
        return compiled_dir / filename

    return _metadata_source


def test_out_emits_only_when_configured(tmp_path: Path) -> None:
    messages: list[str] = []
    bootstrapper = ArtifactBootstrapper(
        compiled_dir=tmp_path / "compiled",
        master_compiled_dir=tmp_path / "master",
        repo_root=tmp_path,
        metadata_source_fn=_metadata_source_factory(tmp_path / "compiled"),
        emit_fn=messages.append,
    )

    bootstrapper._out("hello")
    assert messages == ["hello"]

    silent = ArtifactBootstrapper(
        compiled_dir=tmp_path / "compiled2",
        master_compiled_dir=tmp_path / "master2",
        repo_root=tmp_path,
        metadata_source_fn=_metadata_source_factory(tmp_path / "compiled2"),
    )
    silent._out("ignored")
    assert messages == ["hello"]


def test_ensure_audit_metadata_copies_root_metadata(tmp_path: Path) -> None:
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir()
    for filename in GOVERNANCE_ARTIFACTS[2:]:
        (compiled_dir / filename).write_text(filename, encoding="utf-8")

    bootstrapper = ArtifactBootstrapper(
        compiled_dir=compiled_dir,
        master_compiled_dir=tmp_path / "master",
        repo_root=tmp_path,
        metadata_source_fn=_metadata_source_factory(compiled_dir),
    )

    bootstrapper._ensure_audit_metadata()

    for filename in GOVERNANCE_ARTIFACTS[2:]:
        assert (compiled_dir / "audit" / filename).exists()


def test_ensure_uses_existing_audit_metadata_without_copy(tmp_path: Path) -> None:
    compiled_dir = tmp_path / "compiled"
    audit_dir = compiled_dir / "audit"
    audit_dir.mkdir(parents=True)
    for filename in GOVERNANCE_ARTIFACTS:
        (compiled_dir / filename).write_text(filename, encoding="utf-8")
    for filename in GOVERNANCE_ARTIFACTS[2:]:
        (audit_dir / filename).write_text(f"audit-{filename}", encoding="utf-8")

    bootstrapper = ArtifactBootstrapper(
        compiled_dir=compiled_dir,
        master_compiled_dir=tmp_path / "master",
        repo_root=tmp_path,
        metadata_source_fn=_metadata_source_factory(compiled_dir),
    )

    bootstrapper.ensure()

    for filename in GOVERNANCE_ARTIFACTS[2:]:
        assert (audit_dir / filename).read_text(encoding="utf-8") == f"audit-{filename}"


def test_ensure_bootstraps_and_syncs_from_master(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    compiled_dir = tmp_path / "compiled"
    master_dir = tmp_path / "master"
    master_audit = master_dir / "audit"
    master_audit.mkdir(parents=True)
    compiled_dir.mkdir()
    master_dir.mkdir(exist_ok=True)

    for filename in GOVERNANCE_ARTIFACTS[:2]:
        (master_dir / filename).write_text(filename, encoding="utf-8")
    for filename in GOVERNANCE_ARTIFACTS[2:]:
        (master_audit / filename).write_text(f"audit-{filename}", encoding="utf-8")

    emitted: list[str] = []

    class _Orchestrator:
        def __init__(self, repo_root: str) -> None:
            self.repo_root = repo_root

        def run_full_pipeline(self) -> dict[str, object]:
            return {"full_pipeline_success": True}

    fake_module = types.ModuleType("providence_core.governance_orchestrator")
    fake_module.GovernanceOrchestrator = _Orchestrator
    monkeypatch.setitem(
        sys.modules, "providence_core.governance_orchestrator", fake_module
    )

    bootstrapper = ArtifactBootstrapper(
        compiled_dir=compiled_dir,
        master_compiled_dir=master_dir,
        repo_root=tmp_path,
        metadata_source_fn=lambda filename: compiled_dir / filename,
        emit_fn=emitted.append,
    )
    bootstrapper.ensure()

    assert any("Missing compiled artifacts" in message for message in emitted)
    for filename in GOVERNANCE_ARTIFACTS:
        target = (
            compiled_dir / filename
            if filename.endswith(".msgpack")
            else compiled_dir / "audit" / filename
        )
        assert target.exists()


def test_sync_client_compiled_falls_back_to_master_root_for_metadata(
    tmp_path: Path,
) -> None:
    compiled_dir = tmp_path / "compiled"
    master_dir = tmp_path / "master"
    compiled_dir.mkdir()
    master_dir.mkdir()
    (master_dir / GOVERNANCE_ARTIFACTS[2]).write_text("root-metadata", encoding="utf-8")
    (master_dir / GOVERNANCE_ARTIFACTS[3]).write_text(
        "root-metadata-2", encoding="utf-8"
    )

    bootstrapper = ArtifactBootstrapper(
        compiled_dir=compiled_dir,
        master_compiled_dir=master_dir,
        repo_root=tmp_path,
        metadata_source_fn=lambda filename: compiled_dir / filename,
    )
    bootstrapper._sync_client_compiled_from_master()

    assert (compiled_dir / "audit" / GOVERNANCE_ARTIFACTS[2]).read_text(
        encoding="utf-8"
    ) == "root-metadata"
    assert (compiled_dir / "audit" / GOVERNANCE_ARTIFACTS[3]).read_text(
        encoding="utf-8"
    ) == "root-metadata-2"


def test_ensure_handles_failed_bootstrap_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir()

    class _Orchestrator:
        def __init__(self, repo_root: str) -> None:
            self.repo_root = repo_root

        def run_full_pipeline(self) -> dict[str, object]:
            return {"full_pipeline_success": False}

    fake_module = types.ModuleType("providence_core.governance_orchestrator")
    fake_module.GovernanceOrchestrator = _Orchestrator
    monkeypatch.setitem(
        sys.modules, "providence_core.governance_orchestrator", fake_module
    )

    messages: list[str] = []
    bootstrapper = ArtifactBootstrapper(
        compiled_dir=compiled_dir,
        master_compiled_dir=tmp_path / "master",
        repo_root=tmp_path,
        metadata_source_fn=lambda filename: compiled_dir / filename,
        emit_fn=messages.append,
    )
    bootstrapper.ensure()

    assert any("Bootstrap pipeline failed" in message for message in messages)


def test_ensure_handles_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir()

    fake_module = types.ModuleType("providence_core.governance_orchestrator")

    class _Orchestrator:
        def __init__(self, repo_root: str) -> None:
            raise RuntimeError("boom")

    fake_module.GovernanceOrchestrator = _Orchestrator
    monkeypatch.setitem(
        sys.modules, "providence_core.governance_orchestrator", fake_module
    )

    messages: list[str] = []
    bootstrapper = ArtifactBootstrapper(
        compiled_dir=compiled_dir,
        master_compiled_dir=tmp_path / "master",
        repo_root=tmp_path,
        metadata_source_fn=lambda filename: compiled_dir / filename,
        emit_fn=messages.append,
    )
    bootstrapper.ensure()

    assert any(
        "Failed to bootstrap compiled artifacts" in message for message in messages
    )
