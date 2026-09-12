from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest
import typer
from click.testing import CliRunner

from providence_cli._command_group import (
    COMMAND_SPECS,
    LazyCommandGroup,
    _build_unavailable_command,
    _requested_top_level_command,
)
from providence_cli.main import app

# ---------------------------------------------------------------------------
# _requested_top_level_command
# ---------------------------------------------------------------------------


def _make_ctx(
    args: list[str], protected_args: list[str] | None = None
) -> click.Context:
    ctx = MagicMock(spec=click.Context)
    ctx.args = args
    ctx.protected_args = protected_args or []
    return ctx


def test_requested_top_level_command_from_args() -> None:
    ctx = _make_ctx(["ask", "--flag"])
    assert _requested_top_level_command(ctx) == "ask"


def test_requested_top_level_command_skips_flags() -> None:
    ctx = _make_ctx(["--json", "lint"])
    assert _requested_top_level_command(ctx) == "lint"


def test_requested_top_level_command_empty_returns_empty() -> None:
    ctx = _make_ctx([])
    assert _requested_top_level_command(ctx) == ""


def test_requested_top_level_command_from_protected_args() -> None:
    ctx = _make_ctx([], protected_args=["governance"])
    assert _requested_top_level_command(ctx) == "governance"


# ---------------------------------------------------------------------------
# _build_unavailable_command
# ---------------------------------------------------------------------------


def test_build_unavailable_command_returns_command() -> None:
    exc = ImportError("missing pkg")
    cmd = _build_unavailable_command("mymod", "providence_cli.commands.mymod", exc)
    assert isinstance(cmd, click.Command)
    assert cmd.name == "mymod"


def test_build_unavailable_command_invoke_exits_1() -> None:
    exc = ImportError("missing pkg")
    cmd = _build_unavailable_command("mymod", "providence_cli.commands.mymod", exc)
    runner = CliRunner()
    result = runner.invoke(cmd, [])
    assert result.exit_code == 1
    assert "mymod" in result.output


# ---------------------------------------------------------------------------
# LazyCommandGroup
# ---------------------------------------------------------------------------


def test_list_commands_returns_sorted() -> None:
    group = LazyCommandGroup(name="sdd")
    ctx = MagicMock(spec=click.Context)
    cmds = group.list_commands(ctx)
    assert cmds == sorted(COMMAND_SPECS.keys())


def test_get_command_unknown_returns_none() -> None:
    group = LazyCommandGroup(name="sdd")
    ctx = MagicMock(spec=click.Context)
    assert group.get_command(ctx, "no_such_command") is None


def test_get_command_known_loads_module() -> None:
    group = LazyCommandGroup(name="sdd")
    ctx = MagicMock(spec=click.Context)
    mock_app = typer.Typer()

    @mock_app.command()
    def _dummy() -> None:
        pass

    mock_module = MagicMock()
    mock_module.app = mock_app
    with patch("importlib.import_module", return_value=mock_module):
        cmd = group.get_command(ctx, "lint")
    assert cmd is not None


# ---------------------------------------------------------------------------
# LazyCommandGroup.invoke
# ---------------------------------------------------------------------------


def test_invoke_non_workspace_command_sets_empty_obj() -> None:
    runner = CliRunner()
    captured: list[dict] = []

    @click.command("lint")
    @click.pass_context
    def _lint(ctx: click.Context) -> None:
        captured.append(dict(ctx.obj or {}))

    mock_app = typer.Typer()

    @mock_app.command()
    def dummy() -> None:
        pass

    mock_module = MagicMock()
    mock_module.app = mock_app

    with (
        patch("importlib.import_module", return_value=mock_module),
        patch("providence_cli.utils.profile.governance_gate"),
        patch("providence_cli._command_group.typer_get_command", return_value=_lint),
    ):
        result = runner.invoke(app, ["lint"])
    assert result.exit_code == 0


def test_invoke_typer_click_exit_converted() -> None:
    group = LazyCommandGroup(name="sdd")
    ctx = MagicMock(spec=click.Context)
    ctx.obj = {}
    ctx.args = ["lint"]
    ctx.protected_args = []
    ctx.params = {}

    with (
        patch("providence_cli.utils.profile.governance_gate"),
        patch("click.Group.invoke", side_effect=typer.Exit(2)),
        pytest.raises(click.exceptions.Exit) as exc_info,
    ):
        group.invoke(ctx)
    assert int(exc_info.value.exit_code) == 2


def test_invoke_workspace_required_resolves_profile() -> None:
    group = LazyCommandGroup(name="sdd")
    ctx = MagicMock(spec=click.Context)
    ctx.obj = None
    ctx.args = ["ask"]
    ctx.protected_args = []
    ctx.params = {"profile": None}

    profile_ctx = MagicMock()
    profile_ctx.as_dict.return_value = {"workspace": "client"}

    with (
        patch("providence_cli.utils.profile.governance_gate"),
        patch(
            "providence_core.utils.environment.resolve_profile",
            return_value=profile_ctx,
        ),
        patch("click.Group.invoke", return_value=None),
    ):
        group.invoke(ctx)

    assert ctx.obj.get("workspace") == "client"


def test_invoke_workspace_required_raises_usage_error() -> None:
    from providence_core.utils.environment import WorkspaceNotInitializedError

    group = LazyCommandGroup(name="sdd")
    ctx = MagicMock(spec=click.Context)
    ctx.obj = None
    ctx.args = ["ask"]
    ctx.protected_args = []
    ctx.params = {"profile": None}

    with (
        patch(
            "providence_core.utils.environment.resolve_profile",
            side_effect=WorkspaceNotInitializedError("not init"),
        ),
        patch("providence_cli.utils.profile.governance_gate"),
        pytest.raises(click.UsageError, match="not init"),
    ):
        group.invoke(ctx)


def test_invoke_non_workspace_command_obj_none_sets_empty() -> None:
    group = LazyCommandGroup(name="sdd")
    ctx = MagicMock(spec=click.Context)
    ctx.obj = None
    ctx.args = ["lint"]
    ctx.protected_args = []
    ctx.params = {}

    with (
        patch("providence_cli.utils.profile.governance_gate"),
        patch("click.Group.invoke", return_value=None),
    ):
        group.invoke(ctx)

    assert ctx.obj == {}


def test_get_command_app_not_typer_returns_unavailable() -> None:
    group = LazyCommandGroup(name="sdd")
    ctx = MagicMock(spec=click.Context)
    mock_module = MagicMock()
    mock_module.app = "not_a_typer_instance"
    with patch("importlib.import_module", return_value=mock_module):
        cmd = group.get_command(ctx, "lint")
    assert cmd is not None
    assert cmd.name == "lint"
