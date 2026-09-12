"""Unit tests for DeploymentManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import providence_core
from providence_core.deployment_manager import (
    GOVERNANCE_ARTIFACTS,
    DeploymentManager,
)

_dm_module = providence_core.deployment_manager

pytestmark = pytest.mark.unit


class TestDeploymentManagerInit:
    """Tests for DeploymentManager initialization."""

    def test_init_with_default_paths(self) -> None:
        """Should initialize with default SDD paths."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp/root"),
                "client_compiled": Path("/tmp/client/compiled"),
                "master_compiled": Path("/tmp/master/compiled"),
            }
            manager = DeploymentManager()
            assert manager.repo_root == Path("/tmp/root")
            assert manager.compiled_dir == Path("/tmp/client/compiled")

    def test_init_with_custom_repo_root(self) -> None:
        """Should accept custom repo root path."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/default"),
                "client_compiled": Path("/default/client/compiled"),
                "master_compiled": Path("/default/master/compiled"),
            }
            manager = DeploymentManager(repo_root="/custom/root")
            assert manager.repo_root == Path("/custom/root").resolve()

    def test_init_with_emit_callback(self) -> None:
        """Should accept optional emit callback for logging."""
        emit_fn = MagicMock()
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager(emit=emit_fn)
            assert manager._emit == emit_fn

    def test_runtime_compiled_path_set_correctly(self) -> None:
        """Should set runtime_compiled to .providence/compiled/."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/project"),
                "client_compiled": Path("/project/client/compiled"),
                "master_compiled": Path("/project/master/compiled"),
            }
            manager = DeploymentManager()
            assert manager.runtime_compiled == Path("/project/.providence/compiled")
            assert manager.runtime_audit == Path("/project/.providence/compiled/audit")


class TestDeploymentManagerOut:
    """Tests for output messaging."""

    def test_out_calls_emit_when_provided(self) -> None:
        """_out() should call emit callback when provided."""
        emit_fn = MagicMock()
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager(emit=emit_fn)
            manager._out("test message")
            emit_fn.assert_called_once_with("test message")

    def test_out_silent_when_no_emit(self) -> None:
        """_out() should silently do nothing when emit is None."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager(emit=None)
            # Should not raise
            manager._out("test message")


class TestDeploymentManagerPathStr:
    """Tests for path string normalization."""

    def test_path_str_returns_posix_path(self) -> None:
        """_path_str() should return POSIX-style path string."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager()
            result = manager._path_str(Path("/tmp/foo/bar"))
            assert result == "/tmp/foo/bar"
            assert isinstance(result, str)

    def test_path_str_normalizes_windows_paths(self) -> None:
        """_path_str() should normalize Windows-style paths to POSIX."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager()
            # Even on Windows, as_posix() returns forward slashes
            path = Path("foo") / "bar" / "baz"
            result = manager._path_str(path)
            assert "\\" not in result


class TestDeploymentManagerFailedResult:
    """Tests for failed deployment result generation."""

    def test_failed_result_structure(self) -> None:
        """_failed_result() should return properly structured result."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager()
            result = manager._failed_result()

            assert isinstance(result, dict)
            assert result["success"] is False
            assert "deployed_files" in result
            assert "deployment_location" in result
            assert "checklist" in result
            assert "manifest" in result
            assert "next_steps" in result

    def test_failed_result_has_empty_deployed_files(self) -> None:
        """Failed result should have empty deployed_files."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": Path("/tmp"),
                "client_compiled": Path("/tmp/client"),
                "master_compiled": Path("/tmp/master"),
            }
            manager = DeploymentManager()
            result = manager._failed_result()
            assert result["deployed_files"] == {}


class TestGovernanceArtifacts:
    """Tests for governance artifacts constants."""

    def test_governance_artifacts_is_tuple(self) -> None:
        """GOVERNANCE_ARTIFACTS should be a tuple."""
        assert isinstance(GOVERNANCE_ARTIFACTS, tuple)

    def test_governance_artifacts_contains_required_files(self) -> None:
        """Should contain all required artifact filenames."""
        assert "governance-core.compiled.msgpack" in GOVERNANCE_ARTIFACTS
        assert "governance-client-template.compiled.msgpack" in GOVERNANCE_ARTIFACTS
        assert "metadata-core.json" in GOVERNANCE_ARTIFACTS
        assert "metadata-client-template.json" in GOVERNANCE_ARTIFACTS

    def test_governance_artifacts_not_empty(self) -> None:
        """GOVERNANCE_ARTIFACTS should not be empty."""
        assert len(GOVERNANCE_ARTIFACTS) > 0


class TestDeploymentManagerIntegration:
    """Integration tests for deployment workflow."""

    def test_deploy_with_missing_compiled_files(self, tmp_path: Path) -> None:
        """deploy() should return failed result when compiled files missing."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client" / "compiled",
                "master_compiled": tmp_path / "master" / "compiled",
            }
            manager = DeploymentManager(repo_root=str(tmp_path))
            result = manager.deploy()

            assert result["success"] is False
            assert result["deployed_files"] == {}

    def test_deploy_returns_deployment_result_structure(self, tmp_path: Path) -> None:
        """deploy() should return properly structured DeploymentResult."""
        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client" / "compiled",
                "master_compiled": tmp_path / "master" / "compiled",
            }
            manager = DeploymentManager(repo_root=str(tmp_path))
            result = manager.deploy()

            assert isinstance(result, dict)
            assert "success" in result
            assert "deployed_files" in result
            assert "deployment_location" in result
            assert "checklist" in result
            assert "manifest" in result
            assert "next_steps" in result

    @patch.object(DeploymentManager, "_cleanup_legacy_manifests")
    @patch.object(DeploymentManager, "_get_next_steps")
    @patch.object(DeploymentManager, "_generate_manifest")
    @patch.object(DeploymentManager, "_generate_checklist")
    @patch.object(DeploymentManager, "_validate_compiled_files")
    @patch.object(DeploymentManager, "_verify_deployment")
    @patch.object(DeploymentManager, "_copy_files_transactional")
    @patch.object(DeploymentManager, "_create_runtime_structure")
    def test_deploy_success_with_valid_files(
        self,
        mock_create_runtime: MagicMock,  # noqa: F841
        mock_copy: MagicMock,
        mock_verify: MagicMock,
        mock_validate: MagicMock,
        mock_checklist: MagicMock,
        mock_manifest: MagicMock,
        mock_next_steps: MagicMock,
        mock_cleanup: MagicMock,  # noqa: F841
        tmp_path: Path,
    ) -> None:
        """deploy() should return success when all validations pass."""
        mock_validate.return_value = True
        mock_verify.return_value = True
        mock_copy.return_value = {"file1": "dest1"}  # Non-empty dict for success
        mock_checklist.return_value = {"step1": True}
        mock_manifest.return_value = {"deployed": True}
        mock_next_steps.return_value = ["step1", "step2"]

        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client" / "compiled",
                "master_compiled": tmp_path / "master" / "compiled",
            }
            manager = DeploymentManager(repo_root=str(tmp_path))
            result = manager.deploy()

            assert result["success"] is True
            assert result["deployed_files"] == {"file1": "dest1"}
            assert result["checklist"] == {"step1": True}
            assert result["manifest"] == {"deployed": True}
            assert result["next_steps"] == ["step1", "step2"]
            mock_validate.assert_called()
            mock_copy.assert_called()
            mock_verify.assert_called()


class TestDeploymentManagerEmitMessages:
    """Tests for output messages during deployment."""

    def test_deploy_emits_messages(self, tmp_path: Path) -> None:
        """deploy() should emit messages during execution."""
        emit_fn = MagicMock()

        with patch("providence_core.deployment_manager.get_sdd_paths") as mock_paths:
            mock_paths.return_value = {
                "root": tmp_path,
                "client_compiled": tmp_path / "client" / "compiled",
                "master_compiled": tmp_path / "master" / "compiled",
            }
            manager = DeploymentManager(repo_root=str(tmp_path), emit=emit_fn)
            manager.deploy()

            # Should have called emit at least once
            assert emit_fn.called


def _make_manager(tmp_path: Path) -> DeploymentManager:
    with patch("providence_core.deployment_manager.get_sdd_paths") as mp:
        mp.return_value = {
            "root": tmp_path,
            "client_compiled": tmp_path / "client",
            "master_compiled": tmp_path / "master",
        }
        return DeploymentManager()


class TestPublicApiLazyLoading:
    """Ensure providence_core.__getattr__ lazy exports are exercised."""

    def test_deployment_manager_lazy_export(self) -> None:
        """providence_core.DeploymentManager resolves to the real class."""
        assert providence_core.DeploymentManager is DeploymentManager

    def test_governance_orchestrator_lazy_export(self) -> None:
        """providence_core.GovernanceOrchestrator resolves without ImportError."""
        import importlib

        assert (
            providence_core.GovernanceOrchestrator
            is importlib.import_module(
                "providence_core.governance_orchestrator"
            ).GovernanceOrchestrator
        )

    def test_missing_attribute_raises(self) -> None:
        """providence_core.__getattr__ raises AttributeError for unknown names."""
        with pytest.raises(AttributeError, match="has no attribute"):
            providence_core.__getattr__("_does_not_exist_xyz")


class TestMetadataSource:
    """Tests for _metadata_source path resolution."""

    def test_prefers_audit_subdir_when_file_exists(self, tmp_path: Path) -> None:
        """Returns audit/filename when the file exists there."""
        manager = _make_manager(tmp_path)
        audit_dir = manager.compiled_dir / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        preferred = audit_dir / "metadata.json"
        preferred.write_text("{}", encoding="utf-8")

        result = manager._metadata_source("metadata.json")
        assert result == preferred

    def test_falls_back_to_compiled_root_when_audit_missing(
        self, tmp_path: Path
    ) -> None:
        """Returns compiled_dir/filename when audit copy is absent."""
        manager = _make_manager(tmp_path)
        result = manager._metadata_source("metadata.json")
        assert result == manager.compiled_dir / "metadata.json"


class TestPrivateDelegateMethods:
    """Exercise each private one-liner delegate to cover their bodies."""

    def test_validate_compiled_files_delegates(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with patch(
            "providence_core.deployment_manager.DeploymentValidator.validate_compiled_files",
            return_value=True,
        ) as mock:
            result = manager._validate_compiled_files()
        assert result is True
        mock.assert_called_once()

    def test_create_runtime_structure_delegates(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with patch(
            "providence_core.deployment_manager.DeploymentFileSystem.create_runtime_structure"
        ) as mock:
            manager._create_runtime_structure()
        mock.assert_called_once()

    def test_copy_files_transactional_delegates(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with patch(
            "providence_core.deployment_manager.DeploymentFileSystem.copy_files_transactional",
            return_value={"f": "/p"},
        ) as mock:
            result = manager._copy_files_transactional()
        assert result == {"f": "/p"}
        mock.assert_called_once()

    def test_verify_deployment_delegates(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with patch(
            "providence_core.deployment_manager.DeploymentValidator.verify_deployment",
            return_value=True,
        ) as mock:
            result = manager._verify_deployment()
        assert result is True
        mock.assert_called_once()

    def test_generate_checklist_delegates(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with patch(
            "providence_core.deployment_manager.DeploymentReporter.generate_checklist",
            return_value={"c": True},
        ) as mock:
            result = manager._generate_checklist()
        assert result == {"c": True}
        mock.assert_called_once()

    def test_generate_manifest_delegates(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with patch(
            "providence_core.deployment_manager.DeploymentReporter.generate_manifest",
            return_value={"artifacts": {}},
        ) as mock:
            result = manager._generate_manifest()
        assert result == {"artifacts": {}}
        mock.assert_called_once()

    def test_get_next_steps_delegates(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with patch(
            "providence_core.deployment_manager.DeploymentReporter.get_next_steps",
            return_value=["step1"],
        ) as mock:
            result = manager._get_next_steps()
        assert result == ["step1"]
        mock.assert_called_once()

    def test_cleanup_legacy_manifests_delegates(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with patch(
            "providence_core.deployment_manager.DeploymentReporter.cleanup_legacy_manifests"
        ) as mock:
            manager._cleanup_legacy_manifests()
        mock.assert_called_once()

    def test_get_deployment_status_delegates(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with patch(
            "providence_core.deployment_manager.DeploymentReporter.get_deployment_status",
            return_value={"status": "ok"},
        ) as mock:
            result = manager.get_deployment_status()
        assert result == {"status": "ok"}
        mock.assert_called_once()


class TestDeployFailurePaths:
    """Cover deploy() copy and verification failure branches."""

    def test_copy_empty_result_returns_failed(self, tmp_path: Path) -> None:
        """Empty copy result (falsy dict) → failed result."""
        manager = _make_manager(tmp_path)
        with (
            patch.object(manager, "_validate_compiled_files", return_value=True),
            patch.object(manager, "_create_runtime_structure"),
            patch.object(manager, "_copy_files_transactional", return_value={}),
        ):
            result = manager.deploy()
        assert result["success"] is False

    def test_verify_failure_returns_failed(self, tmp_path: Path) -> None:
        """Verification failure after successful copy → failed result."""
        manager = _make_manager(tmp_path)
        with (
            patch.object(manager, "_validate_compiled_files", return_value=True),
            patch.object(manager, "_create_runtime_structure"),
            patch.object(manager, "_copy_files_transactional", return_value={"f": "p"}),
            patch.object(manager, "_verify_deployment", return_value=False),
        ):
            result = manager.deploy()
        assert result["success"] is False


class TestMainFunction:
    """Cover the module-level main() function."""

    def test_main_success_path(self, tmp_path: Path, capsys) -> None:
        """main() prints deployment complete on success."""

        class _FakeManager:
            def __init__(self, *a, **kw):
                pass

            def deploy(self):
                return {
                    "success": True,
                    "checklist": {"validated": True, "copied": False},
                    "deployment_location": "/tmp/loc",
                    "manifest": {
                        "artifacts": {"core": "/tmp/core.msgpack"},
                        "status": "deployed",
                    },
                    "next_steps": ["git commit", "git tag"],
                }

        with patch.object(_dm_module, "DeploymentManager", _FakeManager):
            _dm_module.main()

        out = capsys.readouterr().out
        assert "DEPLOYMENT COMPLETE" in out
        assert "Status: DEPLOYED" in out

    def test_main_failure_path(self, tmp_path: Path, capsys) -> None:
        """main() prints failure message when deploy returns success=False."""

        class _FakeManager:
            def __init__(self, *a, **kw):
                pass

            def deploy(self):
                return {"success": False}

        with patch.object(_dm_module, "DeploymentManager", _FakeManager):
            _dm_module.main()

        out = capsys.readouterr().out
        assert "failed" in out.lower()

    def test_main_unknown_status(self, capsys) -> None:
        """main() prints 'UNKNOWN' when manifest status is not a string."""

        class _FakeManager:
            def __init__(self, *a, **kw):
                pass

            def deploy(self):
                return {
                    "success": True,
                    "checklist": {},
                    "deployment_location": "/tmp/loc",
                    "manifest": {"artifacts": {}, "status": None},
                    "next_steps": [],
                }

        with patch.object(_dm_module, "DeploymentManager", _FakeManager):
            _dm_module.main()

        out = capsys.readouterr().out
        assert "UNKNOWN" in out
