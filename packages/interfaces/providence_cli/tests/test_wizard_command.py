"""Tests for `providence wizard` command behavior."""

from __future__ import annotations

import builtins
import sys
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from providence_cli.commands.wizard import app


@pytest.fixture(autouse=True)
def mock_deploy_final_template():
    with patch("providence_cli.commands.wizard._deploy_final_template") as mock_deploy:
        yield mock_deploy


def test_wizard_without_subcommand_runs_install_flow() -> None:
    from providence_wizard.contracts import WizardInvocation, WizardResult

    runner = CliRunner()
    recorded: list[WizardInvocation] = []

    def _fake_run_wizard(invocation: WizardInvocation) -> WizardResult:
        recorded.append(invocation)
        return WizardResult(success=True)

    with patch("providence_wizard.contracts.run_wizard", side_effect=_fake_run_wizard):
        result = runner.invoke(app, [])

    assert result.exit_code == 0, result.output
    assert len(recorded) == 1
    assert recorded[0].non_interactive is False


def test_wizard_without_subcommand_deploys_template_by_default(
    mock_deploy_final_template,
) -> None:
    from providence_wizard.contracts import WizardResult

    runner = CliRunner()

    with patch(
        "providence_wizard.contracts.run_wizard",
        return_value=WizardResult(success=True),
    ):
        result = runner.invoke(app, [])

    assert result.exit_code == 0, result.output
    mock_deploy_final_template.assert_called_once_with(None)


def test_wizard_list_shows_public_options() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--list"])

    assert result.exit_code == 0, result.output
    assert "providence wizard" in result.output
    assert "install complete governance and agents" in result.output
    assert "--from-file PATH" in result.output
    assert "--debug" in result.output
    assert "run" not in result.output.lower()


def test_wizard_run_passes_through_debug_flag() -> None:
    from providence_wizard.contracts import WizardInvocation, WizardResult

    runner = CliRunner()
    recorded: list[WizardInvocation] = []

    def _fake_run_wizard(invocation: WizardInvocation) -> WizardResult:
        recorded.append(invocation)
        return WizardResult(success=True)

    with patch("providence_wizard.contracts.run_wizard", side_effect=_fake_run_wizard):
        result = runner.invoke(app, ["run", "--debug"])

    assert result.exit_code == 0, result.output
    assert recorded[0].debug is True


def test_wizard_run_defaults_debug_to_false() -> None:
    from providence_wizard.contracts import WizardInvocation, WizardResult

    runner = CliRunner()
    recorded: list[WizardInvocation] = []

    def _fake_run_wizard(invocation: WizardInvocation) -> WizardResult:
        recorded.append(invocation)
        return WizardResult(success=True)

    with patch("providence_wizard.contracts.run_wizard", side_effect=_fake_run_wizard):
        result = runner.invoke(app, ["run"])

    assert result.exit_code == 0, result.output
    assert recorded[0].debug is False


def test_wizard_run_reports_actionable_error_when_project_root_not_found() -> None:
    runner = CliRunner()
    with patch(
        "providence_wizard.contracts.run_wizard",
        side_effect=RuntimeError(
            "SDD Project root not found. Ensure you are running from within the repository."
        ),
    ):
        result = runner.invoke(app, ["run"])

    assert result.exit_code == 1
    assert "No SDD project context found" in result.output
    assert "providence wizard" in result.output


def test_wizard_run_reraises_unrelated_runtime_error() -> None:
    runner = CliRunner()
    with patch(
        "providence_wizard.contracts.run_wizard",
        side_effect=RuntimeError("unrelated failure"),
    ):
        result = runner.invoke(app, ["run"])

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert "unrelated failure" in str(result.exception)


def test_wizard_run_exits_when_result_is_unsuccessful() -> None:
    from providence_wizard.contracts import WizardResult

    runner = CliRunner()
    with patch(
        "providence_wizard.contracts.run_wizard",
        return_value=WizardResult(success=False, errors=["boom"]),
    ):
        result = runner.invoke(app, ["run"])

    assert result.exit_code == 1


def test_wizard_run_passes_through_from_file_and_non_interactive(
    tmp_path,
) -> None:
    from providence_wizard.contracts import WizardInvocation

    custom_file = tmp_path / "custom-governance.json"
    custom_file.write_text("{}", encoding="utf-8")
    runner = CliRunner()
    recorded: list[WizardInvocation] = []

    def _fake_run_wizard(invocation: WizardInvocation):
        from providence_wizard.contracts import WizardResult

        recorded.append(invocation)
        return WizardResult(success=True)

    with patch("providence_wizard.contracts.run_wizard", side_effect=_fake_run_wizard):
        result = runner.invoke(
            app,
            ["run", "--from-file", str(custom_file), "--non-interactive"],
        )

    assert result.exit_code == 0, result.output
    assert recorded[0].custom_governance_path == custom_file.resolve()
    assert recorded[0].non_interactive is True


def test_run_wizard_skips_deploy_when_only_template_flag_is_internal() -> None:
    from providence_cli.commands.wizard import _run_wizard
    from providence_wizard.contracts import WizardResult

    with (
        patch(
            "providence_wizard.contracts.run_wizard",
            return_value=WizardResult(success=True),
        ),
        patch("providence_cli.commands.wizard._deploy_final_template") as mock_deploy,
    ):
        _run_wizard(None, None, False, only_template=True)

    mock_deploy.assert_not_called()


def test_wizard_default_passes_through_from_file_and_non_interactive(
    tmp_path,
) -> None:
    from providence_wizard.contracts import WizardInvocation

    custom_file = tmp_path / "custom-governance.json"
    custom_file.write_text("{}", encoding="utf-8")
    runner = CliRunner()
    recorded: list[WizardInvocation] = []

    def _fake_run_wizard(invocation: WizardInvocation):
        from providence_wizard.contracts import WizardResult

        recorded.append(invocation)
        return WizardResult(success=True)

    with patch("providence_wizard.contracts.run_wizard", side_effect=_fake_run_wizard):
        result = runner.invoke(
            app,
            ["--from-file", str(custom_file), "--non-interactive"],
        )

    assert result.exit_code == 0, result.output
    assert recorded[0].custom_governance_path == custom_file.resolve()
    assert recorded[0].non_interactive is True


def test_wizard_run_reports_error_when_providence_wizard_not_installed() -> None:
    runner = CliRunner()
    real_import = builtins.__import__

    def _fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "providence_wizard.contracts":
            raise ImportError("No module named 'providence_wizard'")
        return real_import(name, *args, **kwargs)

    with (
        patch.dict(sys.modules, {"providence_wizard.contracts": None}),
        patch("builtins.__import__", side_effect=_fake_import),
    ):
        result = runner.invoke(app, ["run"])

    assert result.exit_code == 1
    assert "ERROR: providence-wizard not installed" in result.output
    assert "providence setup run" in result.output
