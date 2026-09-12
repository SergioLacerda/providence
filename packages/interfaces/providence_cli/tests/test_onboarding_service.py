"""Tests for OnboardingOrchestrator service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


class TestOnboardingOrchestrator:
    def test_run_step_uses_safe_process_runner(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from providence_cli.services.onboarding import OnboardingOrchestrator

        seen: dict[str, object] = {}

        class _Runner:
            def run(self, cmd, cwd=None, env=None, capture_output=None):  # noqa: ANN001
                seen["cmd"] = cmd
                seen["cwd"] = cwd
                seen["env"] = env
                return type("R", (), {"success": True})()

        monkeypatch.setattr(
            "providence_cli.services.onboarding.SafeProcessRunner", lambda: _Runner()
        )
        monkeypatch.setattr(
            "providence_cli.services.onboarding.resolve_sdd_child_cmd",
            lambda: "providence",
        )
        orc = OnboardingOrchestrator(tmp_path)
        assert orc._run_step("x", ["runtime", "status"]) is True
        assert seen["cmd"] == ["providence", "runtime", "status"]
        assert seen["cwd"] == tmp_path
        assert seen["env"]["PYTHONUTF8"] == "1"

    def test_run_step_uses_resolved_executable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_run_step passes the resolved executable, not bare 'sdd'."""
        from providence_cli.services.onboarding import OnboardingOrchestrator

        seen: dict[str, object] = {}

        class _Runner:
            def run(self, cmd, **_kwargs):  # noqa: ANN001
                seen["cmd"] = cmd
                return type("R", (), {"success": True})()

        resolved = "/resolved/bin/providence"
        monkeypatch.setattr(
            "providence_cli.services.onboarding.SafeProcessRunner", lambda: _Runner()
        )
        monkeypatch.setattr(
            "providence_cli.services.onboarding.resolve_sdd_child_cmd", lambda: resolved
        )
        orc = OnboardingOrchestrator(tmp_path)
        orc._run_step("x", ["runtime", "status"])
        assert seen["cmd"] == [resolved, "runtime", "status"]

    def test_run_step_process_permission_error_has_operational_context(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from providence_cli.services.onboarding import OnboardingOrchestrator
        from providence_cli.utils.operational_errors import OperationalCliError

        class _Runner:
            def run(self, cmd, **_kwargs):  # noqa: ANN001
                raise PermissionError("denied")

        monkeypatch.setattr(
            "providence_cli.services.onboarding.SafeProcessRunner", lambda: _Runner()
        )
        monkeypatch.setattr(
            "providence_cli.services.onboarding.resolve_sdd_child_cmd",
            lambda: "providence",
        )

        orc = OnboardingOrchestrator(tmp_path)

        with pytest.raises(OperationalCliError) as exc_info:
            orc._run_step(
                "governance generate",
                ["governance", "generate", "--full-bootstrap"],
            )

        error = exc_info.value
        assert error.step == "governance generate"
        assert error.operation == "run child command"
        assert error.path == tmp_path
        assert "providence governance generate --full-bootstrap" in (
            error.next_hint or ""
        )

    def test_step_governance_skipped_when_artifacts_exist_no_force(
        self, tmp_path: Path
    ) -> None:
        """governance generate is skipped if governance-core.json already exists."""
        from providence_cli.services.onboarding import OnboardingOrchestrator

        compiled = tmp_path / ".providence" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.json").write_text("{}", encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_governance(force=False)
        mock_run.assert_not_called()
        assert result is True

    def test_step_governance_runs_when_force(self, tmp_path: Path) -> None:
        from providence_cli.services.onboarding import OnboardingOrchestrator

        compiled = tmp_path / ".providence" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.json").write_text("{}", encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_governance(force=True)
        mock_run.assert_called_once()
        assert result is True

    def test_step_governance_runs_when_no_artifacts(self, tmp_path: Path) -> None:
        from providence_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            result = orc.step_governance(force=False)
        mock_run.assert_called_once()
        assert result is True

    def test_step_skills_skips_when_seeded(self, tmp_path: Path) -> None:
        from providence_cli.services.onboarding import OnboardingOrchestrator

        seeds = tmp_path / ".providence" / "skills"
        seeds.mkdir(parents=True)
        (seeds / "x").write_text("ok", encoding="utf-8")
        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            assert orc.step_skills(force=False) is True
        mock_run.assert_not_called()

    def test_step_validate_runs_runtime_status(self, tmp_path: Path) -> None:
        from providence_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True) as mock_run:
            assert orc.step_validate() is True
        mock_run.assert_called_once_with(
            "runtime status", ["runtime", "status", "--force"]
        )

    def test_run_stops_on_governance_failure(self, tmp_path: Path) -> None:
        from providence_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=False),
            patch.object(orc, "step_skills") as mock_skills,
            patch.object(orc, "step_validate") as mock_validate,
        ):
            result = orc.run(force=False)
        mock_skills.assert_not_called()
        mock_validate.assert_not_called()
        assert result.success is False
        assert result.failed_step == "governance"

    def test_run_stops_on_skills_failure(self, tmp_path: Path) -> None:
        from providence_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=False),
            patch.object(orc, "step_validate") as mock_validate,
        ):
            result = orc.run(force=False)
        mock_validate.assert_not_called()
        assert result.success is False
        assert result.failed_step == "skills"

    def test_run_returns_success_when_all_pass(self, tmp_path: Path) -> None:
        from providence_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=True),
            patch.object(orc, "step_validate", return_value=True),
        ):
            result = orc.run(force=False)
        assert result.success is True
        assert result.failed_step is None

    def test_run_validate_failure_gives_exit_code_4(self, tmp_path: Path) -> None:
        from providence_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=True),
            patch.object(orc, "step_validate", return_value=False),
        ):
            result = orc.run(force=False)
        assert result.success is False
        assert result.failed_step == "validate"
        assert result.exit_code == 4

    def test_run_does_not_install_git_hooks(self, tmp_path: Path) -> None:
        from providence_cli.services.onboarding import OnboardingOrchestrator

        orc = OnboardingOrchestrator(tmp_path)
        with (
            patch.object(orc, "step_governance", return_value=True),
            patch.object(orc, "step_skills", return_value=True),
            patch.object(orc, "step_validate", return_value=True),
        ):
            result = orc.run(force=False)
        assert result.success is True

    def test_onboarding_has_no_git_hook_step(self, tmp_path: Path) -> None:
        from providence_cli.services.onboarding import OnboardingOrchestrator

        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)

        orc = OnboardingOrchestrator(tmp_path)
        assert not hasattr(orc, "step_hooks")
