"""Coverage tests for GovernanceOrchestrator failure paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from providence_core.governance_orchestrator import GovernanceOrchestrator

pytestmark = pytest.mark.unit


def _make_paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "root": tmp_path,
        "source_spec": tmp_path / "docs" / "spec",
        "master_compiled": tmp_path / ".providence" / "compiled",
        "master_build": tmp_path / ".providence" / "build",
        "client_compiled": tmp_path / ".providence" / "client" / "compiled",
        "client_build": tmp_path / ".providence" / "client" / "build",
    }


def _make_orchestrator(
    tmp_path: Path, profile: str | None = None
) -> GovernanceOrchestrator:
    with patch("providence_core.governance_orchestrator.get_sdd_paths") as mp:
        mp.return_value = _make_paths(tmp_path)
        return GovernanceOrchestrator(
            repo_root=str(tmp_path),
            profile=profile,
        )


class TestInitProfileBranches:
    def test_compiled_dir_override_skips_profile_resolution(
        self, tmp_path: Path
    ) -> None:
        custom = str(tmp_path / "custom_compiled")
        with patch("providence_core.governance_orchestrator.get_sdd_paths") as mp:
            mp.return_value = _make_paths(tmp_path)
            orch = GovernanceOrchestrator(
                repo_root=str(tmp_path),
                compiled_dir=custom,
            )
        assert orch.compiled_dir == Path(custom)

    def test_client_profile_uses_client_paths(self, tmp_path: Path) -> None:
        with patch("providence_core.governance_orchestrator.get_sdd_paths") as mp:
            mp.return_value = _make_paths(tmp_path)
            with patch(
                "providence_core.governance_orchestrator.GovernanceOrchestrator._resolve_active_profile",
                return_value="client",
            ):
                orch = GovernanceOrchestrator(repo_root=str(tmp_path))
        assert "client" in str(orch.compiled_dir)

    def test_resolve_active_profile_falls_back_to_master_on_error(
        self, tmp_path: Path
    ) -> None:
        with patch(
            "providence_core.governance_orchestrator.resolve_profile",
            side_effect=RuntimeError,
        ):
            result = GovernanceOrchestrator._resolve_active_profile(tmp_path)
        assert result == "master"


class TestRunFullPipelinePhase1Fail:
    def test_returns_early_when_phase1_fails(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        with patch.object(
            orch, "_run_phase_1", return_value={"success": False, "error": "boom"}
        ):
            result = orch.run_full_pipeline()
        assert result["full_pipeline_success"] is False
        assert result["phase_2"] == {}

    def test_emit_callback_called_on_phase1_fail(self, tmp_path: Path) -> None:
        messages: list[str] = []
        with patch("providence_core.governance_orchestrator.get_sdd_paths") as mp:
            mp.return_value = _make_paths(tmp_path)
            orch = GovernanceOrchestrator(repo_root=str(tmp_path), emit=messages.append)
        with patch.object(orch, "_run_phase_1", return_value={"success": False}):
            orch.run_full_pipeline()
        assert any("PHASE 1 failed" in m for m in messages)


class TestRunFullPipelinePhase2Fail:
    def test_returns_early_when_phase2_fails(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        phase1_ok = {
            "success": True,
            "core_item_count": 5,
            "client_item_count": 2,
            "core_fingerprint": "a" * 32,
            "client_fingerprint": "b" * 32,
        }
        with (
            patch.object(orch, "_run_phase_1", return_value=phase1_ok),
            patch.object(
                orch, "_run_phase_2", return_value={"success": False, "error": "bad"}
            ),
        ):
            result = orch.run_full_pipeline()
        assert result["full_pipeline_success"] is False
        assert result["phase_1"]["success"] is True

    def test_emit_callback_called_on_phase2_fail(self, tmp_path: Path) -> None:
        messages: list[str] = []
        with patch("providence_core.governance_orchestrator.get_sdd_paths") as mp:
            mp.return_value = _make_paths(tmp_path)
            orch = GovernanceOrchestrator(repo_root=str(tmp_path), emit=messages.append)
        phase1_ok = {
            "success": True,
            "core_item_count": 1,
            "client_item_count": 0,
            "core_fingerprint": "a" * 32,
            "client_fingerprint": "b" * 32,
        }
        with (
            patch.object(orch, "_run_phase_1", return_value=phase1_ok),
            patch.object(orch, "_run_phase_2", return_value={"success": False}),
        ):
            orch.run_full_pipeline()
        assert any("PHASE 2 failed" in m for m in messages)


class TestRunFullPipelineValidationFail:
    def test_validation_fail_sets_pipeline_success_false(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        phase1_ok = {
            "success": True,
            "core_item_count": 1,
            "client_item_count": 0,
            "core_fingerprint": "fp1",
            "client_fingerprint": "fp2",
        }
        phase2_ok = {
            "success": True,
            "core_msgpack_file": "a.msgpack",
            "client_msgpack_file": "b.msgpack",
        }
        with (
            patch.object(orch, "_run_phase_1", return_value=phase1_ok),
            patch.object(orch, "_run_phase_2", return_value=phase2_ok),
            patch.object(orch, "_validate_full_pipeline", return_value=False),
        ):
            result = orch.run_full_pipeline()
        assert result["full_pipeline_success"] is False
        assert result["validated"] is False


class TestRunPhase1Exception:
    def test_phase1_exception_returns_failed(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        with patch(
            "providence_core.governance_orchestrator.PipelineBuilder",
            side_effect=RuntimeError("no spec"),
        ):
            result = orch._run_phase_1()
        assert result["success"] is False
        assert "no spec" in result.get("error", "")


class TestRunPhase2Exception:
    def test_phase2_exception_returns_failed(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        with patch(
            "providence_core.governance_orchestrator.CompilerRunner",
            side_effect=RuntimeError("compile error"),
        ):
            result = orch._run_phase_2()
        assert result["success"] is False
        assert "compile error" in result.get("error", "")

    def test_phase2_compile_validation_fails(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {
            "core_msgpack_file": "a.msgpack",
            "client_msgpack_file": "b.msgpack",
        }
        mock_compiler.validate_compilation_detailed.return_value = {
            "ok": False,
            "errors": ["file not found: a.msgpack"],
            "checks": [],
        }
        with patch(
            "providence_core.governance_orchestrator.CompilerRunner",
            return_value=mock_compiler,
        ):
            result = orch._run_phase_2()
        assert result["success"] is False
        assert "file not found: a.msgpack" in result.get("error", "")


class TestGetDeploymentSummary:
    def test_returns_expected_keys(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path)
        summary = orch.get_deployment_summary()
        assert summary["status"] == "ready_for_deployment"
        assert "artifacts" in summary
        assert "next_step" in summary
