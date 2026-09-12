"""Tests for providence_wizard.main  public entry point."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from providence_wizard.main import run_wizard


class TestRunWizard:
    def test_success_returns_normally(self, tmp_path: Path) -> None:
        """Completes without exception when wizard succeeds."""
        with patch(
            "providence_wizard.main.run_wizard_contract",
            return_value=type("Result", (), {"success": True})(),
        ) as mock:
            run_wizard(repo_root=tmp_path, output_dir=tmp_path / "out")
        invocation = mock.call_args.args[0]
        assert invocation.project_root == tmp_path
        assert invocation.output_path == tmp_path / "out"

    def test_failure_exits_with_code_1(self, tmp_path: Path) -> None:
        """Calls sys.exit(1) when wizard returns False."""
        with (
            patch(
                "providence_wizard.main.run_wizard_contract",
                return_value=type("Result", (), {"success": False})(),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            run_wizard(repo_root=tmp_path)
        assert exc_info.value.code == 1

    def test_default_repo_root_uses_cwd(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """When repo_root is None, Path.cwd() is used."""
        monkeypatch.chdir(tmp_path)
        recorded: list = []

        def _capture(invocation) -> object:
            recorded.append((invocation.project_root, invocation.output_path))
            return type("Result", (), {"success": True})()

        with patch("providence_wizard.main.run_wizard_contract", side_effect=_capture):
            run_wizard()

        assert recorded[0][0] == tmp_path
        assert recorded[0][1] is None

    def test_output_dir_passed_through(self, tmp_path: Path) -> None:
        """Custom output_dir is forwarded to run_interactive_wizard."""
        out = tmp_path / "custom_output"
        recorded: list = []

        def _capture(invocation) -> object:
            recorded.append(invocation.output_path)
            return type("Result", (), {"success": True})()

        with patch("providence_wizard.main.run_wizard_contract", side_effect=_capture):
            run_wizard(repo_root=tmp_path, output_dir=out)

        assert recorded[0] == out

    def test_success_with_output_dir_none(self, tmp_path: Path) -> None:
        """output_dir=None is the default and is forwarded correctly."""
        recorded: list = []

        def _capture(invocation) -> object:
            recorded.append(invocation.output_path)
            return type("Result", (), {"success": True})()

        with patch("providence_wizard.main.run_wizard_contract", side_effect=_capture):
            run_wizard(repo_root=tmp_path)

        assert recorded[0] is None
