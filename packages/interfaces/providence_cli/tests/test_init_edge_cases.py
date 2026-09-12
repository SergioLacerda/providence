"""Tests for providence init command  _run_cli_step helper, edge cases, profile display."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from providence_cli.commands.init_steps import _run_cli_step

# ---------------------------------------------------------------------------
# _run_cli_step helper
# ---------------------------------------------------------------------------


class TestRunCliStep:
    def test_returns_true_on_zero_exit(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = _run_cli_step(
                "governance compile", ["governance", "compile"], tmp_path
            )
        assert result is True

    def test_returns_false_on_nonzero_exit(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = _run_cli_step("runtime status", ["runtime", "status"], tmp_path)
        assert result is False

    def test_invokes_providence_cli_module(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_cli.commands.init_steps.resolve_sdd_child_cmd",
                return_value="providence",
            ),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            _run_cli_step("test", ["governance", "compile"], tmp_path)
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "providence"
        assert cmd[1:] == ["governance", "compile"]

    def test_sets_pythonutf8_env(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            _run_cli_step("test", ["arg"], tmp_path)
        env = mock_run.call_args[1]["env"]
        assert env.get("PYTHONUTF8") == "1"


# ---------------------------------------------------------------------------
# init  error branches and existing-profile display
# ---------------------------------------------------------------------------


class TestInitEdgeCases:
    """Cover error branches in the init command."""

    def test_exits_1_when_parent_workspace_exists(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from providence_cli.commands.init import app

        runner = CliRunner()
        parent_root = tmp_path / "parent"
        profile_path = parent_root / ".providence" / "profile"
        profile_path.parent.mkdir(parents=True)
        profile_path.write_text(
            "[sdd]\ntype = client\nname = client\nworkspace_id = ws-parent\n",
            encoding="utf-8",
        )

        def _fake_cwd():
            return tmp_path / "parent" / "child"

        with (
            patch("providence_cli.commands.init.Path.cwd", _fake_cwd),
            patch(
                "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
                return_value=parent_root,
            ),
        ):
            result = runner.invoke(app, ["--default", "--no-bootstrap"])
        assert result.exit_code == 1, result.output
        assert not (tmp_path / "parent" / "child" / ".providence" / "profile").exists()

    def test_allows_init_when_parent_sdd_dir_has_no_profile(
        self, tmp_path: Path
    ) -> None:
        """A bare `.providence/` ancestor (e.g. the global CLI toolchain cache under
        the user's home directory) must not block init  only a real
        initialized workspace (`.providence/profile` present) should."""
        from typer.testing import CliRunner

        from providence_cli.commands.init import app

        runner = CliRunner()
        parent_root = tmp_path / "parent"
        (parent_root / ".providence" / "bin").mkdir(parents=True)

        def _fake_cwd():
            return tmp_path / "parent" / "child"

        with (
            patch("providence_cli.commands.init.Path.cwd", _fake_cwd),
            patch(
                "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
                return_value=None,
            ),
        ):
            result = runner.invoke(app, ["--default", "--no-bootstrap"])
        assert result.exit_code == 0, result.output
        assert (tmp_path / "parent" / "child" / ".providence" / "profile").exists()

    def test_allows_project_workspace_when_home_workspace_exists(
        self, tmp_path: Path
    ) -> None:
        from typer.testing import CliRunner

        from providence_cli.commands.init import app

        runner = CliRunner()
        home = tmp_path / "home"
        project = home / "dev" / "project"
        (home / ".providence").mkdir(parents=True)
        (project / ".git").mkdir(parents=True)

        def _fake_cwd():
            return project

        with patch("providence_cli.commands.init.Path.cwd", _fake_cwd):
            result = runner.invoke(app, ["--default", "--no-bootstrap"])

        assert result.exit_code == 0, result.output
        assert (project / ".providence" / "profile").exists()
        assert "Workspace initialized" in result.output

    def test_exits_1_when_profile_exists_and_no_force(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from providence_cli.commands.init import app

        runner = CliRunner()
        profile_path = tmp_path / ".providence" / "profile"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            "[sdd]\ntype = client\nname = client\nworkspace_id = ws-old\n",
            encoding="utf-8",
        )

        def _fake_cwd():
            return tmp_path

        with (
            patch("providence_cli.commands.init.Path.cwd", _fake_cwd),
            patch(
                "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
                return_value=None,
            ),
        ):
            result = runner.invoke(app, [])
        assert result.exit_code == 1
        assert "already initialized" in result.output

    def test_exits_2_when_type_invalid(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from providence_cli.commands.init import app

        runner = CliRunner()

        def _fake_cwd():
            return tmp_path

        mock_ctx = MagicMock(type="client", name="client", workspace_id="ws-test")
        with (
            patch("providence_cli.commands.init.Path.cwd", _fake_cwd),
            patch(
                "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
                return_value=None,
            ),
            patch("providence_cli.commands.init.write_profile", return_value=mock_ctx),
        ):
            result = runner.invoke(app, ["--type", "invalid"])
        assert result.exit_code == 2

    def test_prints_overwrite_soft_warning_when_force(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from providence_cli.commands.init import app

        runner = CliRunner()
        profile_path = tmp_path / ".providence" / "profile"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            "[sdd]\ntype = client\nname = client\nworkspace_id = ws-old\n",
            encoding="utf-8",
        )

        def _fake_cwd():
            return tmp_path

        mock_ctx = MagicMock(type="client", name="client", workspace_id="ws-new")
        with (
            patch("providence_cli.commands.init.Path.cwd", _fake_cwd),
            patch(
                "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
                return_value=None,
            ),
            patch("providence_cli.commands.init.write_profile", return_value=mock_ctx),
        ):
            result = runner.invoke(app, ["--force", "--no-bootstrap"])
        assert result.exit_code == 0
        assert "profile overwritten" in result.output

    def test_telemetry_failure_does_not_abort_init(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from providence_cli.commands.init import app

        runner = CliRunner()

        def _fake_cwd():
            return tmp_path

        mock_ctx = MagicMock(type="client", name="client", workspace_id="ws-test")
        with (
            patch("providence_cli.commands.init.Path.cwd", _fake_cwd),
            patch(
                "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
                return_value=None,
            ),
            patch("providence_cli.commands.init.write_profile", return_value=mock_ctx),
            patch(
                "providence_runtime.telemetry.TelemetrySink",
                side_effect=Exception("telemetry down"),
            ),
        ):
            result = runner.invoke(app, ["--no-bootstrap"])
        assert result.exit_code == 0
        assert "Workspace initialized" in result.output

    def test_profile_permission_error_exits_without_traceback(
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
                side_effect=PermissionError("denied"),
            ),
        ):
            result = runner.invoke(app, ["--type", "client"])

        assert result.exit_code == 1
        assert "Could not write SDD workspace profile" in result.output
        assert "Step: profile" in result.output
        assert str(tmp_path / ".providence" / "profile") in result.output
        assert "providence init --force" in result.output
        assert "Traceback" not in result.output

    def test_runtime_marker_permission_error_exits_without_traceback(
        self, tmp_path: Path
    ) -> None:
        from typer.testing import CliRunner

        from providence_cli.commands.init import app

        runner = CliRunner()
        mock_ctx = MagicMock(type="client", name="client", workspace_id="ws-test")

        with (
            patch("providence_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch(
                "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
                return_value=None,
            ),
            patch("providence_cli.commands.init.write_profile", return_value=mock_ctx),
            patch(
                "pathlib.Path.touch",
                side_effect=PermissionError("denied"),
            ),
        ):
            result = runner.invoke(app, ["--type", "client"])

        assert result.exit_code == 1
        assert "Could not initialize SDD runtime marker" in result.output
        assert "Operation: create runtime marker" in result.output
        assert "Traceback" not in result.output

    def test_onboarding_operational_error_exits_without_traceback(
        self, tmp_path: Path
    ) -> None:
        from typer.testing import CliRunner

        from providence_cli.commands.init import app
        from providence_cli.utils.operational_errors import OperationalCliError

        runner = CliRunner()
        mock_ctx = MagicMock(type="client", name="client", workspace_id="ws-test")

        with (
            patch("providence_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch(
                "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
                return_value=None,
            ),
            patch("providence_cli.commands.init.write_profile", return_value=mock_ctx),
            patch(
                "providence_cli.commands.init_bootstrap.OnboardingOrchestrator"
            ) as MockOrch,
        ):
            MockOrch.return_value.run.side_effect = OperationalCliError(
                "Bootstrap step failed while running 'governance generate'.",
                cause=PermissionError("denied"),
                command="providence init",
                step="governance generate",
                operation="run child command",
                path=tmp_path,
                next_hint="retry: providence governance generate --full-bootstrap",
            )
            result = runner.invoke(app, ["--type", "client"])

        assert result.exit_code == 1
        assert "Bootstrap step failed" in result.output
        assert "Step: governance generate" in result.output
        assert "retry: providence governance generate" in result.output
        assert "Traceback" not in result.output


class TestShowExistingProfile:
    def test_prints_profile_fields(self, tmp_path: Path, capsys) -> None:
        import configparser

        from providence_cli.commands.init import _show_existing_profile

        profile = tmp_path / ".providence" / "profile"
        profile.parent.mkdir(parents=True, exist_ok=True)
        cfg = configparser.ConfigParser()
        cfg["sdd"] = {"type": "client", "name": "my-project", "workspace_id": "ws-1"}
        with open(profile, "w", encoding="utf-8") as f:
            cfg.write(f)

        _show_existing_profile(profile, tmp_path)
        out = capsys.readouterr().out
        assert "type" in out
        assert "client" in out
