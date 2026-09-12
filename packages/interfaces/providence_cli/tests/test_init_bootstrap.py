"""Tests for providence init command  --full-bootstrap orchestration (Phase 4)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _invoke_init(tmp_path: Path, extra_args: list[str], step_side_effect=None):
    """Helper: invoke `providence init` with cwd mocked to tmp_path."""
    from typer.testing import CliRunner

    from providence_cli.commands.init import app

    runner = CliRunner()

    def _fake_cwd():
        return tmp_path

    mock_profile_ctx = MagicMock(type="client", name="client", workspace_id="ws-test")

    step_mock = None
    if step_side_effect is not None:
        step_mock = MagicMock(side_effect=step_side_effect)

    with (
        patch(
            "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
            return_value=None,
        ),
        patch(
            "providence_cli.commands.init.write_profile", return_value=mock_profile_ctx
        ),
        patch("providence_cli.commands.init.Path.cwd", _fake_cwd),
    ):
        if step_mock is not None:
            with patch("providence_cli.commands.init_steps._run_cli_step", step_mock):
                result = runner.invoke(app, extra_args)
        else:
            result = runner.invoke(app, extra_args)

    return result, step_mock


class TestInitFullBootstrap:
    """--type client runs OnboardingOrchestrator by default (opt-out via --no-bootstrap)."""

    def _invoke_with_orchestrator(
        self, tmp_path: Path, args: list[str], orchestrator_result=None
    ):
        from typer.testing import CliRunner

        from providence_cli.commands.init import app
        from providence_cli.services.onboarding import OnboardingResult

        runner = CliRunner()

        def _fake_cwd():
            return tmp_path

        mock_ctx = MagicMock(type="client", name="client", workspace_id="ws-test")

        if orchestrator_result is None:
            orchestrator_result = OnboardingResult(success=True, exit_code=0)

        with (
            patch("providence_cli.commands.init.Path.cwd", _fake_cwd),
            patch(
                "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
                return_value=None,
            ),
            patch("providence_cli.commands.init.write_profile", return_value=mock_ctx),
            patch(
                "providence_cli.commands.init_bootstrap.OnboardingOrchestrator"
            ) as MockOrch,
        ):
            mock_instance = MagicMock()
            mock_instance.run.return_value = orchestrator_result
            MockOrch.return_value = mock_instance
            result = runner.invoke(app, args)
        return result, MockOrch

    def test_client_type_runs_orchestrator_by_default(self, tmp_path: Path) -> None:
        """--type client invokes OnboardingOrchestrator without any extra flag."""
        result, MockOrch = self._invoke_with_orchestrator(
            tmp_path, ["--type", "client"]
        )
        assert result.exit_code == 0, result.output
        MockOrch.return_value.run.assert_called_once_with(force=False)

    def test_bootstrap_success_prints_onboarding_complete(self, tmp_path: Path) -> None:
        result, _ = self._invoke_with_orchestrator(tmp_path, ["--type", "client"])
        assert result.exit_code == 0
        assert "Onboarding complete" in result.output

    def test_bootstrap_failure_exits_with_orchestrator_exit_code(
        self, tmp_path: Path
    ) -> None:
        from providence_cli.services.onboarding import OnboardingResult

        result, _ = self._invoke_with_orchestrator(
            tmp_path,
            ["--type", "client"],
            orchestrator_result=OnboardingResult(
                success=False,
                failed_step="governance",
                exit_code=1,
                messages=["failed"],
            ),
        )
        assert result.exit_code == 1

    def test_no_bootstrap_prints_next_steps(self, tmp_path: Path) -> None:
        """--no-bootstrap skips orchestrator and shows manual next-steps block."""
        result, _ = _invoke_init(tmp_path, ["--no-bootstrap"])
        assert result.exit_code == 0
        assert "providence governance generate" in result.output
        assert "providence runtime status" in result.output


class TestBootstrapDefault:
    """--type client runs OnboardingOrchestrator by default; --no-bootstrap skips it."""

    def _invoke(self, tmp_path: Path, args: list[str], orchestrator_result=None):
        from unittest.mock import MagicMock, patch

        from typer.testing import CliRunner

        from providence_cli.commands.init import app
        from providence_cli.services.onboarding import OnboardingResult

        runner = CliRunner()
        mock_ctx = MagicMock()
        mock_ctx.type = "client"
        mock_ctx.name = args[args.index("--name") + 1] if "--name" in args else "test"
        mock_ctx.workspace_id = "test-id"

        if orchestrator_result is None:
            orchestrator_result = OnboardingResult(success=True, exit_code=0)

        with (
            patch("providence_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch(
                "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
                return_value=None,
            ),
            patch(
                "providence_cli.commands.init.write_profile",
                return_value=mock_ctx,
            ),
            patch(
                "providence_cli.commands.init_bootstrap.OnboardingOrchestrator"
            ) as MockOrch,
        ):
            mock_instance = MagicMock()
            mock_instance.run.return_value = orchestrator_result
            MockOrch.return_value = mock_instance
            result = runner.invoke(app, args)
        return result, MockOrch

    def test_client_type_runs_orchestrator_by_default(self, tmp_path: Path) -> None:
        result, MockOrch = self._invoke(
            tmp_path, ["--type", "client", "--name", "test", "--force"]
        )
        MockOrch.return_value.run.assert_called_once_with(force=True)
        assert result.exit_code == 0

    def test_no_bootstrap_skips_orchestrator(self, tmp_path: Path) -> None:
        result, MockOrch = self._invoke(
            tmp_path,
            ["--type", "client", "--name", "test", "--no-bootstrap", "--force"],
        )
        MockOrch.assert_not_called()
        assert result.exit_code == 0

    def test_master_type_does_not_bootstrap(self, tmp_path: Path) -> None:
        result, MockOrch = self._invoke(tmp_path, ["--type", "master", "--force"])
        MockOrch.assert_not_called()
        assert result.exit_code == 0

    def test_orchestrator_failure_exits_with_its_exit_code(
        self, tmp_path: Path
    ) -> None:
        from providence_cli.services.onboarding import OnboardingResult

        result, _ = self._invoke(
            tmp_path,
            ["--type", "client", "--force"],
            orchestrator_result=OnboardingResult(
                success=False,
                failed_step="governance",
                exit_code=2,
                messages=["governance generate failed"],
            ),
        )
        assert result.exit_code == 2


class TestInitDefaultFlag:
    """--default fills in type=client, name=local-dev, force=True when unset."""

    def _invoke(self, tmp_path: Path, args: list[str], orchestrator_result=None):
        from unittest.mock import MagicMock, patch

        from typer.testing import CliRunner

        from providence_cli.commands.init import app
        from providence_cli.services.onboarding import OnboardingResult

        runner = CliRunner()
        mock_ctx = MagicMock()
        mock_ctx.type = "client"
        mock_ctx.name = "local-dev"
        mock_ctx.workspace_id = "test-id"

        if orchestrator_result is None:
            orchestrator_result = OnboardingResult(success=True, exit_code=0)

        with (
            patch("providence_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch(
                "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
                return_value=None,
            ),
            patch(
                "providence_cli.commands.init.write_profile",
                return_value=mock_ctx,
            ) as mock_write_profile,
            patch(
                "providence_cli.commands.init_bootstrap.OnboardingOrchestrator"
            ) as MockOrch,
        ):
            mock_instance = MagicMock()
            mock_instance.run.return_value = orchestrator_result
            MockOrch.return_value = mock_instance
            result = runner.invoke(app, args)
        return result, MockOrch, mock_write_profile

    def test_default_alone_resolves_client_local_dev_force(
        self, tmp_path: Path
    ) -> None:
        result, MockOrch, mock_write_profile = self._invoke(tmp_path, ["--default"])
        assert result.exit_code == 0, result.output
        mock_write_profile.assert_called_once_with(
            tmp_path, "client", "local-dev", "en"
        )
        MockOrch.return_value.run.assert_called_once_with(force=True)

    def test_default_does_not_override_explicit_type(self, tmp_path: Path) -> None:
        """--default still fills in --name (unset) even when --type is explicit."""
        result, MockOrch, mock_write_profile = self._invoke(
            tmp_path, ["--default", "--type", "master"]
        )
        assert result.exit_code == 0, result.output
        mock_write_profile.assert_called_once_with(
            tmp_path, "master", "local-dev", "en"
        )
        MockOrch.assert_not_called()

    def test_default_does_not_override_explicit_name(self, tmp_path: Path) -> None:
        result, MockOrch, mock_write_profile = self._invoke(
            tmp_path, ["--default", "--name", "custom-name"]
        )
        assert result.exit_code == 0, result.output
        mock_write_profile.assert_called_once_with(
            tmp_path, "client", "custom-name", "en"
        )
        MockOrch.return_value.run.assert_called_once_with(force=True)

    def test_default_does_not_override_explicit_language(self, tmp_path: Path) -> None:
        """--default fills in --language only when it wasn't explicitly set."""
        result, MockOrch, mock_write_profile = self._invoke(
            tmp_path, ["--default", "--language", "pt-br"]
        )
        assert result.exit_code == 0, result.output
        mock_write_profile.assert_called_once_with(
            tmp_path, "client", "local-dev", "pt-BR"
        )
        MockOrch.return_value.run.assert_called_once_with(force=True)

    def test_default_does_not_override_explicit_force_false(
        self, tmp_path: Path
    ) -> None:
        """--default sets force=True only when --force isn't explicitly passed.

        Typer/click has no way to pass an explicit "false" override for a
        store_true flag, so this documents that --default always wins for
        force unless a future --no-force flag is introduced.
        """
        result, MockOrch, _ = self._invoke(tmp_path, ["--default"])
        assert result.exit_code == 0, result.output
        MockOrch.return_value.run.assert_called_once_with(force=True)

    def test_without_default_behavior_unchanged(self, tmp_path: Path) -> None:
        result, MockOrch, mock_write_profile = self._invoke(
            tmp_path, ["--type", "client", "--name", "test", "--force"]
        )
        assert result.exit_code == 0, result.output
        mock_write_profile.assert_called_once_with(tmp_path, "client", "test", None)
        MockOrch.return_value.run.assert_called_once_with(force=True)

    def test_incompatible_providence_core_write_profile_exits_with_upgrade_hint(
        self, tmp_path: Path
    ) -> None:
        from typer.testing import CliRunner

        from providence_cli.commands.init import app

        runner = CliRunner()
        with (
            patch("providence_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch(
                "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
                return_value=None,
            ),
            patch(
                "providence_cli.commands.init.write_profile",
                side_effect=TypeError(
                    "write_profile() takes 3 positional arguments but 4 were given"
                ),
            ),
        ):
            result = runner.invoke(app, ["--default"])

        assert result.exit_code == 1
        assert "Installed providence-core is incompatible" in result.output
        assert "uv tool upgrade providence-cli" in result.output


class TestInitLanguageFlag:
    """--language accepts case-insensitive en|pt-BR and normalizes before storage."""

    def _invoke(self, tmp_path: Path, args: list[str]):
        return TestInitDefaultFlag()._invoke(tmp_path, args)

    @pytest.mark.parametrize(
        ("raw", "canonical"),
        [
            ("en", "en"),
            ("EN", "en"),
            ("pt-br", "pt-BR"),
            ("PT-BR", "pt-BR"),
            ("pt-BR", "pt-BR"),
        ],
    )
    def test_normalizes_case_insensitive_input(
        self, tmp_path: Path, raw: str, canonical: str
    ) -> None:
        result, _, mock_write_profile = self._invoke(
            tmp_path, ["--type", "client", "--name", "test", "--language", raw]
        )
        assert result.exit_code == 0, result.output
        mock_write_profile.assert_called_once_with(
            tmp_path, "client", "test", canonical
        )

    def test_invalid_language_exits_with_error(self, tmp_path: Path) -> None:
        result, _, mock_write_profile = self._invoke(
            tmp_path, ["--type", "client", "--name", "test", "--language", "fr"]
        )
        assert result.exit_code == 2
        assert "--language must be" in result.output
        mock_write_profile.assert_not_called()
