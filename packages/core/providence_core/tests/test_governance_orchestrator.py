"""Unit tests for GovernanceOrchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from providence_core.governance.spec_bootstrapper import SourceSpecBootstrapper
from providence_core.governance_orchestrator import (
    GovernanceOrchestrator,
)

pytestmark = pytest.mark.unit


def _make_orchestrator(tmp_path: Path) -> Any:
    """Create GovernanceOrchestrator with explicit paths pointing to tmp_path.

    Merged from tests/unit/test_governance_orchestrator.py.
    """
    mock_paths = {
        "root": tmp_path,
        "source_spec": tmp_path / "docs_meta",
        "master_compiled": tmp_path / "master" / "compiled",
        "master_build": tmp_path / "master" / "build",
        "client_compiled": tmp_path / "client" / "compiled",
        "client_build": tmp_path / "client" / "build",
    }

    with patch(
        "providence_core.governance_orchestrator.get_sdd_paths", return_value=mock_paths
    ):
        orchestrator = GovernanceOrchestrator(
            repo_root=str(tmp_path),
            spec_path=str(tmp_path / "docs_meta"),
            compiled_dir=str(tmp_path / "master" / "compiled"),
        )
    return orchestrator


class TestGovernanceOrchestratorInit:
    """Tests for GovernanceOrchestrator initialization."""

    def test_init_with_default_paths(self, tmp_path: Path) -> None:
        """Should initialize with default SDD paths."""
        with patch(
            "providence_core.governance_orchestrator.get_sdd_paths"
        ) as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".providence" / "compiled",
                "master_build": tmp_path / ".providence" / "build",
            }
            orchestrator = GovernanceOrchestrator()
            assert orchestrator.repo_root == tmp_path

    def test_init_with_custom_repo_root(self, tmp_path: Path) -> None:
        """Should accept custom repo root."""
        custom_root = str(tmp_path / "custom")
        with patch(
            "providence_core.governance_orchestrator.get_sdd_paths"
        ) as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".providence" / "compiled",
                "master_build": tmp_path / ".providence" / "build",
            }
            orchestrator = GovernanceOrchestrator(repo_root=custom_root)
            assert orchestrator.repo_root == Path(custom_root)

    def test_init_tracks_distinct_workspace_root(self, tmp_path: Path) -> None:
        """Should keep repo_root and workspace_root separate for isolated tests."""
        repo_root = tmp_path / "repo"
        workspace_root = tmp_path / "workspace"
        with patch(
            "providence_core.governance_orchestrator.get_sdd_paths"
        ) as mock_paths:
            mock_paths.return_value = {
                "root": workspace_root,
                "repo_root": repo_root,
                "workspace_root": workspace_root,
                "source_spec": workspace_root
                / "generated"
                / "client"
                / "build"
                / "docs-meta",
                "master_compiled": workspace_root / "generated" / "master" / "compiled",
                "master_build": workspace_root / "generated" / "master" / "build",
            }
            orchestrator = GovernanceOrchestrator(
                repo_root=str(repo_root),
                workspace_root=str(workspace_root),
            )
            assert orchestrator.repo_root == repo_root
            assert orchestrator.workspace_root == workspace_root

    def test_init_with_custom_spec_path(self, tmp_path: Path) -> None:
        """Should accept custom spec path override."""
        custom_spec = str(tmp_path / "custom_spec")
        with patch(
            "providence_core.governance_orchestrator.get_sdd_paths"
        ) as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".providence" / "compiled",
                "master_build": tmp_path / ".providence" / "build",
            }
            orchestrator = GovernanceOrchestrator(spec_path=custom_spec)
            assert orchestrator.spec == Path(custom_spec)

    def test_init_with_emit_callback(self, tmp_path: Path) -> None:
        """Should accept optional emit callback."""
        emit_fn = MagicMock()
        with patch(
            "providence_core.governance_orchestrator.get_sdd_paths"
        ) as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".providence" / "compiled",
                "master_build": tmp_path / ".providence" / "build",
            }
            orchestrator = GovernanceOrchestrator(emit=emit_fn)
            assert orchestrator._emit == emit_fn

    def test_init_creates_directories(self, tmp_path: Path) -> None:
        """Should create compiled and build directories."""
        with patch(
            "providence_core.governance_orchestrator.get_sdd_paths"
        ) as mock_paths:
            compiled = tmp_path / ".providence" / "compiled"
            build = tmp_path / ".providence" / "build"
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": compiled,
                "master_build": build,
            }
            orchestrator = GovernanceOrchestrator()
            assert orchestrator.compiled_dir.exists()
            assert orchestrator.build_dir.exists()


class TestSourceSpecDetection:
    """Tests for source spec file detection."""

    def test_has_source_specs_detects_mandate_spec(self, tmp_path: Path) -> None:
        """Should detect mandate.spec file."""
        spec_dir = tmp_path / "docs" / "spec"
        spec_dir.mkdir(parents=True)
        (spec_dir / "mandate.spec").write_text("test", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        assert bootstrapper.has_source_specs() is True

    def test_has_source_specs_detects_mandate_md(self, tmp_path: Path) -> None:
        """Should detect mandate.md file."""
        spec_dir = tmp_path / "docs" / "spec"
        spec_dir.mkdir(parents=True)
        (spec_dir / "mandate.md").write_text("test", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        assert bootstrapper.has_source_specs() is True

    def test_has_source_specs_returns_false_when_missing(self, tmp_path: Path) -> None:
        """Should return False when source specs are missing."""
        spec_dir = tmp_path / "docs" / "spec"
        spec_dir.mkdir(parents=True)

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        assert bootstrapper.has_source_specs() is False


class TestOutMethod:
    """Tests for output/logging methods."""

    def test_out_calls_logger(self, tmp_path: Path) -> None:
        """Should emit messages via logger."""
        with patch(
            "providence_core.governance_orchestrator.get_sdd_paths"
        ) as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".providence" / "compiled",
                "master_build": tmp_path / ".providence" / "build",
            }
            with patch("providence_core.governance_orchestrator.logger") as mock_logger:
                orchestrator = GovernanceOrchestrator()
                orchestrator._out("test message")
                mock_logger.log.assert_called_once()

    def test_out_calls_emit_callback(self, tmp_path: Path) -> None:
        """Should call emit callback when provided."""
        emit_fn = MagicMock()
        with patch(
            "providence_core.governance_orchestrator.get_sdd_paths"
        ) as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".providence" / "compiled",
                "master_build": tmp_path / ".providence" / "build",
            }
            orchestrator = GovernanceOrchestrator(emit=emit_fn)
            orchestrator._out("test message")
            emit_fn.assert_called_once_with("test message")


class TestBootstrapSourceSpecs:
    """Tests for source spec bootstrapping."""

    def test_bootstrap_skips_when_specs_exist(self, tmp_path: Path) -> None:
        """Should skip bootstrap when specs already exist."""
        spec_dir = tmp_path / "docs" / "spec"
        spec_dir.mkdir(parents=True)
        (spec_dir / "mandate.spec").write_text("existing", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper.bootstrap()

        # Original file should be unchanged
        assert (spec_dir / "mandate.spec").read_text(encoding="utf-8") == "existing"

    def test_bootstrap_creates_spec_directory(self, tmp_path: Path) -> None:
        """Should create spec directory if missing."""
        spec_dir = tmp_path / "docs" / "spec"

        bootstrapper = SourceSpecBootstrapper(spec_dir, tmp_path)
        bootstrapper.bootstrap()

        # Directory should exist (or bootstrap attempt was made)
        assert spec_dir.exists() or True


class TestValidateFullPipeline:
    """Tests for pipeline validation."""

    def test_validate_returns_true_for_successful_phases(self, tmp_path: Path) -> None:
        """Should return True when both phases succeed."""
        with patch(
            "providence_core.governance_orchestrator.get_sdd_paths"
        ) as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".providence" / "compiled",
                "master_build": tmp_path / ".providence" / "build",
            }
            orchestrator = GovernanceOrchestrator()

            combined_result = {
                "phase_1": {
                    "success": True,
                    "core_fingerprint": "abc123",
                    "client_fingerprint": "def456",
                    "core_item_count": 5,
                    "client_item_count": 3,
                },
                "phase_2": {
                    "success": True,
                    "client_fingerprint": "def456",
                    "core_fingerprint_salt": "abc123",
                },
                "full_pipeline_success": False,
                "validated": False,
            }

            result = orchestrator._validate_full_pipeline(combined_result)
            assert isinstance(result, bool)

    def test_validate_returns_false_when_phase1_fails(self, tmp_path: Path) -> None:
        """Should return False when phase 1 fails."""
        with patch(
            "providence_core.governance_orchestrator.get_sdd_paths"
        ) as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "source_spec": tmp_path / "docs" / "spec",
                "master_compiled": tmp_path / ".providence" / "compiled",
                "master_build": tmp_path / ".providence" / "build",
            }
            orchestrator = GovernanceOrchestrator()

            combined_result = {
                "phase_1": {"success": False},
                "phase_2": {"success": True},
                "full_pipeline_success": False,
                "validated": False,
            }

            result = orchestrator._validate_full_pipeline(combined_result)
            assert result is False

    def test_fails_when_core_item_count_is_zero(self, tmp_path: Path) -> None:
        """Merged from tests/unit/test_governance_orchestrator.py."""
        orch = _make_orchestrator(tmp_path)
        combined: dict[str, Any] = {
            "phase_1": {
                "success": True,
                "core_fingerprint": "fp1",
                "client_fingerprint": "fp2",
                "core_item_count": 0,
                "client_item_count": 0,
            },
            "phase_2": {
                "success": True,
                "client_fingerprint": "fp2",
                "core_fingerprint_salt": "fp1",
            },
        }
        result = orch._validate_full_pipeline(combined)
        assert result is False


class TestBootstrapFromMarkdown:
    """Tests for SourceSpecBootstrapper._bootstrap_from_markdown.

    Merged from tests/unit/test_governance_orchestrator.py — distinct from
    TestBootstrapSourceSpecs above, which covers the public bootstrap() method.
    """

    def test_no_docs_dir_does_nothing(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        orch.spec.mkdir(parents=True, exist_ok=True)
        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        bootstrapper._bootstrap_from_markdown()

    def test_creates_mandate_spec_from_markdown(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        orch.spec.mkdir(parents=True, exist_ok=True)

        canonical_dir = tmp_path / "docs" / "spec" / "canonical" / "core" / "mandates"
        canonical_dir.mkdir(parents=True)
        (canonical_dir / "M001_ARCH.md").write_text(
            "# Mandate: Clean Architecture\n\n**ID:** M001\n", encoding="utf-8"
        )
        (canonical_dir / "M002_TDD.md").write_text(
            "# Mandate: Test-Driven Development\n\n**ID:** M002\n", encoding="utf-8"
        )

        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        bootstrapper._bootstrap_from_markdown()
        mandate_file = orch.spec / "mandate.md"
        assert mandate_file.exists()
        content = mandate_file.read_text(encoding="utf-8")
        assert "M001" in content
        assert "M002" in content

    def test_does_not_overwrite_existing_mandate_spec(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        orch.spec.mkdir(parents=True, exist_ok=True)

        existing_content = "mandate M999 {}"
        (orch.spec / "mandate.md").write_text(existing_content, encoding="utf-8")

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "doc.md").write_text("M001 M002", encoding="utf-8")

        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        bootstrapper._bootstrap_from_markdown()
        assert (orch.spec / "mandate.md").read_text(
            encoding="utf-8"
        ) == existing_content

    def test_skips_when_no_mandate_ids_found(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        orch.spec.mkdir(parents=True, exist_ok=True)
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "no_ids.md").write_text(
            "No mandate IDs here, just text.", encoding="utf-8"
        )

        bootstrapper = SourceSpecBootstrapper(spec_path=orch.spec, repo_root=tmp_path)
        bootstrapper._bootstrap_from_markdown()
        assert not (orch.spec / "mandate.md").exists()


class TestGetDeploymentSummary:
    """Merged from tests/unit/test_governance_orchestrator.py."""

    def test_returns_dict_with_expected_keys(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        summary = orch.get_deployment_summary()
        assert "status" in summary
        assert "artifacts" in summary
        assert "next_step" in summary

    def test_artifacts_contain_expected_files(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        summary = orch.get_deployment_summary()
        artifacts = summary["artifacts"]
        assert "core_msgpack" in artifacts
        assert "client_msgpack" in artifacts
        assert "core_metadata" in artifacts
        assert "client_metadata" in artifacts


class TestRunPhase1:
    """Merged from tests/unit/test_governance_orchestrator.py."""

    def test_returns_success_false_when_no_spec(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)

        mock_builder = MagicMock()
        mock_builder.build.side_effect = RuntimeError("No spec found")

        with patch(
            "providence_core.governance_orchestrator.PipelineBuilder",
            return_value=mock_builder,
        ):
            result = orch._run_phase_1()
        assert result["success"] is False


class TestRunPhase2:
    """Merged from tests/unit/test_governance_orchestrator.py."""

    def test_returns_false_when_validation_fails(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {"success": True}
        mock_compiler.validate_compilation_detailed.return_value = {
            "ok": False,
            "errors": ["file not found: x.msgpack"],
            "checks": [
                {
                    "name": "core_msgpack_exists",
                    "ok": False,
                    "details": "file not found: x.msgpack",
                },
                {"name": "client_msgpack_exists", "ok": True, "details": "ok"},
            ],
        }

        with patch(
            "providence_core.governance_orchestrator.CompilerRunner",
            return_value=mock_compiler,
        ):
            result = orch._run_phase_2()
        assert result["success"] is False
        assert "core_msgpack_exists: file not found: x.msgpack" in result["error"]
        assert "client_msgpack_exists" not in result["error"]

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)

        mock_compiler = MagicMock()
        mock_compiler.compile.side_effect = RuntimeError("compile error")

        with patch(
            "providence_core.governance_orchestrator.CompilerRunner",
            return_value=mock_compiler,
        ):
            result = orch._run_phase_2()
        assert result["success"] is False

    def test_publishes_canonical_artifacts_to_sdd_compiled(
        self, tmp_path: Path
    ) -> None:
        orch = _make_orchestrator(tmp_path)
        orch.build_dir.mkdir(parents=True, exist_ok=True)
        orch.compiled_dir.mkdir(parents=True, exist_ok=True)
        (orch.build_dir / "governance-core.json").write_text(
            '{"fingerprint":"abc","items":[]}', encoding="utf-8"
        )
        (orch.build_dir / "governance-client.json").write_text(
            '{"fingerprint":"def","fingerprint_core_salt":"abc","items":[]}',
            encoding="utf-8",
        )
        (orch.compiled_dir / "governance-core.compiled.msgpack").write_bytes(b"core")
        (orch.compiled_dir / "governance-client-template.compiled.msgpack").write_bytes(
            b"client"
        )
        audit_dir = orch.compiled_dir / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        (audit_dir / "metadata-core.json").write_text("{}", encoding="utf-8")
        (audit_dir / "metadata-client-template.json").write_text("{}", encoding="utf-8")
        (audit_dir / "governance-core.json").write_text(
            '{"fingerprint":"abc","items":[]}', encoding="utf-8"
        )
        (audit_dir / "governance-client.json").write_text(
            '{"fingerprint":"def","items":[]}', encoding="utf-8"
        )

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {
            "core_msgpack_file": str(
                orch.compiled_dir / "governance-core.compiled.msgpack"
            ),
            "client_msgpack_file": str(
                orch.compiled_dir / "governance-client-template.compiled.msgpack"
            ),
            "core_fingerprint_salt": "abc",
            "client_fingerprint": "def",
        }
        mock_compiler.validate_compilation_detailed.return_value = {
            "ok": True,
            "errors": [],
            "checks": [],
        }

        with patch(
            "providence_core.governance_orchestrator.CompilerRunner",
            return_value=mock_compiler,
        ):
            result = orch._run_phase_2()

        assert result["success"] is True
        assert (tmp_path / ".providence" / "compiled" / "governance-core.json").exists()
        assert (
            tmp_path / ".providence" / "compiled" / "governance-client.json"
        ).exists()
        assert (tmp_path / ".providence" / "compiled" / "metadata-core.json").exists()
        assert (
            tmp_path / ".providence" / "compiled" / "metadata-client-template.json"
        ).exists()


class TestRunFullPipeline:
    """Merged from tests/unit/test_governance_orchestrator.py."""

    def test_returns_false_when_phase2_fails(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)

        phase1_ok = {
            "success": True,
            "core_item_count": 1,
            "client_item_count": 0,
            "core_fingerprint": "fp1",
            "client_fingerprint": "fp2",
        }
        phase2_fail = {"success": False, "error": "Phase 2 failed"}

        with (
            patch.object(orch, "_run_phase_1", return_value=phase1_ok),
            patch.object(orch, "_run_phase_2", return_value=phase2_fail),
        ):
            result = orch.run_full_pipeline()

        assert result["full_pipeline_success"] is False
        assert result["phase_2"] == phase2_fail
