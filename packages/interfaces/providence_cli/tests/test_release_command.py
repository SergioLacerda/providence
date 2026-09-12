"""Tests for providence_cli.commands.release  build command coverage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()
pytestmark = pytest.mark.unit


class TestReleaseBuild:
    def test_build_package_not_installed_exits_1(self) -> None:
        with (
            patch(
                "providence_cli.utils.profile.enforce_profile_policy", return_value=None
            ),
            patch(
                "providence_cli.utils.dev_deps.check_module_available",
                return_value=False,
            ),
        ):
            result = runner.invoke(app, ["release", "build"])
        assert result.exit_code == 1
        assert "not available in this environment" in result.output

    def test_build_success(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)
        with (
            patch(
                "providence_cli.utils.profile.enforce_profile_policy", return_value=None
            ),
            patch(
                "providence_cli.utils.dev_deps.check_module_available",
                return_value=True,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["release", "build"])
        assert result.exit_code == 0

    def test_non_zero_exit_error_exits_1(self) -> None:
        from providence_core.utils.process import ProcessNonZeroExitError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessNonZeroExitError("build failed")
        with (
            patch(
                "providence_cli.utils.profile.enforce_profile_policy", return_value=None
            ),
            patch(
                "providence_cli.utils.dev_deps.check_module_available",
                return_value=True,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["release", "build"])
        assert result.exit_code == 1
        assert "build failed" in result.output

    def test_authorization_error_exits_2(self) -> None:
        from providence_core.utils.process import ProcessAuthorizationError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessAuthorizationError("blocked")
        with (
            patch(
                "providence_cli.utils.profile.enforce_profile_policy", return_value=None
            ),
            patch(
                "providence_cli.utils.dev_deps.check_module_available",
                return_value=True,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["release", "build"])
        assert result.exit_code == 2
        assert "blocked by policy" in result.output

    def test_timeout_error_exits_124(self) -> None:
        from providence_core.utils.process import ProcessTimeoutError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessTimeoutError(
            ["python", "-m", "build"], 30.0
        )
        with (
            patch(
                "providence_cli.utils.profile.enforce_profile_policy", return_value=None
            ),
            patch(
                "providence_cli.utils.dev_deps.check_module_available",
                return_value=True,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["release", "build"])
        assert result.exit_code == 124
        assert "timed out" in result.output

    def test_spawn_error_exits_127(self) -> None:
        from providence_core.utils.process import ProcessSpawnError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessSpawnError("cannot spawn")
        with (
            patch(
                "providence_cli.utils.profile.enforce_profile_policy", return_value=None
            ),
            patch(
                "providence_cli.utils.dev_deps.check_module_available",
                return_value=True,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["release", "build"])
        assert result.exit_code == 127
        assert "could not start" in result.output
