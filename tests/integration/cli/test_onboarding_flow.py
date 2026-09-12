"""Integration tests: OnboardingOrchestrator flow in isolated tmp workspaces."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from providence_cli.services.onboarding import OnboardingOrchestrator

pytestmark = pytest.mark.integration


class TestOnboardingOrchestratorIntegration:
    """End-to-end flow tests that exercise orchestrator logic with mocked subprocess."""

    def test_full_success_flow(self, tmp_path: Path) -> None:
        """All steps pass → OnboardingResult.success is True."""
        orc = OnboardingOrchestrator(tmp_path)
        with patch.object(orc, "_run_step", return_value=True):
            result = orc.run(force=True)
        assert result.success is True
        assert result.failed_step is None
        assert result.exit_code == 0

    def test_stops_on_governance_failure(self, tmp_path: Path) -> None:
        """Governance failure stops immediately; skills and validate never run."""
        orc = OnboardingOrchestrator(tmp_path)
        steps_called: list[str] = []

        def spy(_label: str, args: list[str]) -> bool:
            steps_called.append(args[0])
            return False  # always fail

        with patch.object(orc, "_run_step", side_effect=spy):
            result = orc.run(force=True)

        assert result.success is False
        assert result.failed_step == "governance"
        assert result.exit_code == 2
        assert "skills" not in steps_called
        assert "runtime" not in steps_called

    def test_stops_on_skills_failure(self, tmp_path: Path) -> None:
        """Skills failure stops immediately; validate never runs."""
        orc = OnboardingOrchestrator(tmp_path)
        call_count = 0

        def spy(_label: str, _args: list[str]) -> bool:
            nonlocal call_count
            call_count += 1
            return call_count == 1  # governance passes, skills fails

        with patch.object(orc, "_run_step", side_effect=spy):
            result = orc.run(force=True)

        assert result.success is False
        assert result.failed_step == "skills"
        assert result.exit_code == 3

    def test_validate_failure_gives_exit_code_4(self, tmp_path: Path) -> None:
        """Validate failure gives exit code 4 with diagnostic message."""
        orc = OnboardingOrchestrator(tmp_path)
        call_count = 0

        def spy(_label: str, _args: list[str]) -> bool:
            nonlocal call_count
            call_count += 1
            return call_count < 3  # governance and skills pass, validate fails

        with patch.object(orc, "_run_step", side_effect=spy):
            result = orc.run(force=True)

        assert result.success is False
        assert result.failed_step == "validate"
        assert result.exit_code == 4
        assert any("governance not active" in m for m in result.messages)

    def test_governance_skipped_when_artifacts_exist_no_force(
        self, tmp_path: Path
    ) -> None:
        """governance generate is skipped if compiled artifacts already exist."""
        compiled = tmp_path / ".providence" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.json").write_text('{"items":[]}', encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        steps_called: list[str] = []

        def spy(_label: str, args: list[str]) -> bool:
            steps_called.append(args[0])
            return True

        with patch.object(orc, "_run_step", side_effect=spy):
            result = orc.run(force=False)

        assert "governance" not in steps_called
        assert result.success is True

    def test_governance_runs_when_force_even_if_artifacts_exist(
        self, tmp_path: Path
    ) -> None:
        """--force always re-runs governance generate."""
        compiled = tmp_path / ".providence" / "compiled"
        compiled.mkdir(parents=True)
        (compiled / "governance-core.json").write_text('{"items":[]}', encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        steps_called: list[str] = []

        def spy(_label: str, args: list[str]) -> bool:
            steps_called.append(args[0])
            return True

        with patch.object(orc, "_run_step", side_effect=spy):
            result = orc.run(force=True)

        assert "governance" in steps_called
        assert result.success is True

    def test_skills_skipped_when_seeds_exist_no_force(self, tmp_path: Path) -> None:
        """skills bootstrap is skipped if .providence/skills/ already has content."""
        skills_dir = tmp_path / ".providence" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "some-skill.yaml").write_text("name: test", encoding="utf-8")

        orc = OnboardingOrchestrator(tmp_path)
        steps_called: list[str] = []

        def spy(_label: str, args: list[str]) -> bool:
            steps_called.append(args[0])
            return True

        with patch.object(orc, "_run_step", side_effect=spy):
            result = orc.run(force=False)

        assert "skills" not in steps_called
        assert result.success is True
