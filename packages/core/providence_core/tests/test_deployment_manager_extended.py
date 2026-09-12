"""Extended tests for deployment manager (reach 80% coverage)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from providence_core.deployment_manager import DeploymentManager

pytestmark = pytest.mark.unit


class TestDeploymentManagerPathHandling:
    """Tests for path handling edge cases."""

    def test_path_str_with_relative_paths(self, tmp_path: Path) -> None:
        """Should convert relative paths to strings."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client",
                "master_compiled": tmp_path / "master",
            }
            manager = DeploymentManager()
            result = manager._path_str(Path("relative/path"))
            assert isinstance(result, str)
            assert "relative" in result

    def test_path_str_with_root_paths(self, tmp_path: Path) -> None:
        """Should handle absolute paths."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client",
                "master_compiled": tmp_path / "master",
            }
            manager = DeploymentManager()
            result = manager._path_str(tmp_path)
            assert isinstance(result, str)


class TestDeploymentManagerOutputHandling:
    """Tests for output/logging behavior."""

    def test_out_emits_message(self, tmp_path: Path) -> None:
        """Should emit output messages."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client",
                "master_compiled": tmp_path / "master",
            }
            manager = DeploymentManager()
            # Should not raise
            manager._out("test message")

    def test_out_with_emit_callback(self, tmp_path: Path) -> None:
        """Should call emit callback when provided."""
        emit_fn = MagicMock()
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client",
                "master_compiled": tmp_path / "master",
            }
            manager = DeploymentManager(emit=emit_fn)
            manager._out("message")
            emit_fn.assert_called_once_with("message")


class TestDeploymentManagerFailedResultEdgeCases:
    """Tests for failed result generation edge cases."""

    def test_failed_result_empty_collections(self, tmp_path: Path) -> None:
        """Failed result should have empty but valid collections."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client",
                "master_compiled": tmp_path / "master",
            }
            manager = DeploymentManager()
            result = manager._failed_result()

            assert isinstance(result["deployed_files"], dict)
            assert isinstance(result["checklist"], dict)
            assert isinstance(result["manifest"], dict)
            assert isinstance(result["next_steps"], list)

    def test_failed_result_success_flag(self, tmp_path: Path) -> None:
        """Failed result should always have success=False."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client",
                "master_compiled": tmp_path / "master",
            }
            manager = DeploymentManager()
            result = manager._failed_result()

            assert result["success"] is False


class TestDeploymentManagerRuntimePaths:
    """Tests for runtime path configuration."""

    def test_runtime_compiled_path_structure(self, tmp_path: Path) -> None:
        """Runtime compiled path should follow .providence/compiled structure."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client",
                "master_compiled": tmp_path / "master",
            }
            manager = DeploymentManager()

            assert ".providence" in str(manager.runtime_compiled)
            assert "compiled" in str(manager.runtime_compiled)

    def test_runtime_audit_path_exists(self, tmp_path: Path) -> None:
        """Runtime audit path should be under runtime_compiled."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client",
                "master_compiled": tmp_path / "master",
            }
            manager = DeploymentManager()

            assert "audit" in str(manager.runtime_audit)
            assert ".providence" in str(manager.runtime_audit)


class TestDeploymentManagerInitialization:
    """Tests for initialization variations."""

    def test_init_creates_runtime_directories(self, tmp_path: Path) -> None:
        """Should set up runtime directory paths."""
        client_compiled = tmp_path / "client" / "compiled"
        client_compiled.mkdir(parents=True, exist_ok=True)

        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            compiled = tmp_path / ".providence" / "compiled"
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": client_compiled,
                "master_compiled": compiled,
            }
            manager = DeploymentManager()

            # compiled_dir should be set to client_compiled
            assert manager.compiled_dir == client_compiled

    def test_init_with_string_repo_root(self, tmp_path: Path) -> None:
        """Should accept string repo_root."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client",
                "master_compiled": tmp_path / "master",
            }
            manager = DeploymentManager(repo_root=str(tmp_path))

            assert isinstance(manager.repo_root, Path)


class TestGovernanceArtifactsConstant:
    """Tests for GOVERNANCE_ARTIFACTS constant."""

    def test_governance_artifacts_is_tuple_not_list(self) -> None:
        """GOVERNANCE_ARTIFACTS should be immutable tuple."""
        from providence_core.deployment_manager import GOVERNANCE_ARTIFACTS

        assert isinstance(GOVERNANCE_ARTIFACTS, tuple)

    def test_governance_artifacts_items_are_strings(self) -> None:
        """All items should be strings."""
        from providence_core.deployment_manager import GOVERNANCE_ARTIFACTS

        for item in GOVERNANCE_ARTIFACTS:
            assert isinstance(item, str)

    def test_governance_artifacts_expected_count(self) -> None:
        """Should contain expected number of artifacts."""
        from providence_core.deployment_manager import GOVERNANCE_ARTIFACTS

        assert len(GOVERNANCE_ARTIFACTS) >= 4
