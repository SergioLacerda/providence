"""Tests for Phase 4 deterministic error messages with next-step hints.

Verifies that CLI commands emit actionable 'Next:' guidance on failure
so users can self-remediate without consulting docs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from providence_cli.commands.doctor import app as doctor_app
from providence_cli.commands.governance import app as governance_app
from providence_cli.services.runtime_preflight import PreflightResult

# ---------------------------------------------------------------------------
# governance compile  next-step on failure
# ---------------------------------------------------------------------------


class TestGovernanceCompileNextStep:
    """governance compile must emit Next: hint on failure."""

    def test_pipeline_exception_emits_next_step(self) -> None:
        runner = CliRunner()

        with patch(
            "providence_cli.commands.governance.run_compile",
            side_effect=RuntimeError("unexpected failure"),
        ):
            result = runner.invoke(governance_app, ["compile"])

        assert result.exit_code != 0
        assert "Next:" in result.output

    def test_pipeline_failure_emits_next_step(self) -> None:
        """When pipeline raises, Next: hint is emitted via handle_cli_errors."""
        runner = CliRunner()

        with patch(
            "providence_cli.commands.governance.run_compile",
            side_effect=RuntimeError("pipeline returned failure"),
        ):
            result = runner.invoke(governance_app, ["compile"])

        assert result.exit_code != 0
        assert "Next:" in result.output


# ---------------------------------------------------------------------------
# governance validate  next-step on failure
# ---------------------------------------------------------------------------


class TestGovernanceValidateNextStep:
    """governance validate must emit Next: hint when checks fail."""

    def test_failed_checks_emit_next_step(self) -> None:
        runner = CliRunner()

        with (
            patch(
                "providence_cli.utils.loader.validate_governance_path",
                return_value=False,
            ),
            patch(
                "providence_cli.services.governance_config_reader.check_files_accessible",
                return_value=False,
            ),
            patch(
                "providence_cli.services.governance_config_reader.check_fingerprints_valid",
                return_value=False,
            ),
            patch(
                "providence_cli.services.governance_config_reader.check_no_conflicts",
                return_value=False,
            ),
            patch(
                "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
                return_value=(False, "inconsistent artifacts"),
            ),
            patch(
                "providence_cli.services.runtime_preflight.run_runtime_preflight",
                return_value=PreflightResult(passed=False, reason="drift"),
            ),
        ):
            result = runner.invoke(governance_app, ["validate", "--skip-handshake"])

        assert result.exit_code != 0
        assert "Next:" in result.output

    def test_validate_exception_emits_next_step(self) -> None:
        runner = CliRunner()

        with patch(
            "providence_cli.commands._governance_command_registry.run_governance_validate_cmd",
            side_effect=RuntimeError("disk error"),
        ):
            result = runner.invoke(governance_app, ["validate"])

        assert result.exit_code != 0
        assert "Next:" in result.output


# ---------------------------------------------------------------------------
# doctor  next-step when spec not found
# ---------------------------------------------------------------------------


class TestDoctorNextStep:
    """doctor must emit Next: hint when spec file is missing."""

    def test_missing_spec_emits_next_step(self, tmp_path: Path) -> None:
        runner = CliRunner()

        missing_spec = tmp_path / "nonexistent.yaml"

        # Patch providence_integration so the ImportError guard passes
        fake_providence_integration = MagicMock()
        fake_engine_mod = MagicMock()
        fake_engine_mod.IntegrationEngine = MagicMock()

        with (
            patch.dict(
                sys.modules,
                {
                    "providence_integration": fake_providence_integration,
                    "providence_integration.engine": MagicMock(),
                    "providence_integration.engine.integration_engine": fake_engine_mod,
                },
            ),
            patch(
                "providence_cli.commands.doctor._get_default_spec",
                return_value=missing_spec,
            ),
            patch(
                "providence_cli.commands.doctor.find_workspace_root",
                return_value=tmp_path,
                create=True,
            ),
        ):
            result = runner.invoke(doctor_app, ["run"])

        assert result.exit_code != 0
        assert "Next:" in result.output
