"""Unit tests for `providence init` command logic.

Tests call the init() Typer callback directly to bypass Typer's type registry,
which does not support Literal[...] annotations in CliRunner.invoke().
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from providence_cli.commands.init import init

pytestmark = pytest.mark.unit


class TestInitCommand:
    """providence init creates .providence/profile and handles edge cases."""

    def test_creates_profile_in_clean_directory(self, tmp_path: Path) -> None:
        with (
            patch("providence_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch(
                "providence_cli.commands.init._find_blocking_parent_workspace",
                return_value=None,
            ),
        ):
            init(
                MagicMock(),
                type="client",
                name="test-ws",
                force=False,
                no_bootstrap=True,
                default=False,
                language=None,
                list_commands=False,
            )
        profile_path = tmp_path / ".providence" / "profile"
        assert profile_path.exists()
        content = profile_path.read_text(encoding="utf-8")
        assert "client" in content

    def test_exits_1_if_already_initialized_without_force(self, tmp_path: Path) -> None:
        # Create profile first
        with (
            patch("providence_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch(
                "providence_cli.commands.init._find_blocking_parent_workspace",
                return_value=None,
            ),
        ):
            init(
                MagicMock(),
                type="client",
                name="first",
                force=False,
                no_bootstrap=True,
                default=False,
                language=None,
                list_commands=False,
            )
        # Second init without --force must exit 1
        with (
            pytest.raises(typer.Exit) as exc_info,
            patch("providence_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch(
                "providence_cli.commands.init._find_blocking_parent_workspace",
                return_value=None,
            ),
        ):
            init(
                MagicMock(),
                type="client",
                name="second",
                force=False,
                no_bootstrap=True,
                default=False,
                language=None,
                list_commands=False,
            )
        assert exc_info.value.exit_code == 1

    def test_force_overwrites_existing_profile(self, tmp_path: Path) -> None:
        with (
            patch("providence_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch(
                "providence_cli.commands.init._find_blocking_parent_workspace",
                return_value=None,
            ),
        ):
            init(
                MagicMock(),
                type="client",
                name="first",
                force=False,
                no_bootstrap=True,
                default=False,
                language=None,
                list_commands=False,
            )
            init(
                MagicMock(),
                type="master",
                name="second",
                force=True,
                no_bootstrap=True,
                default=False,
                language=None,
                list_commands=False,
            )
        content = (tmp_path / ".providence" / "profile").read_text(encoding="utf-8")
        assert "master" in content

    def test_default_name_equals_type(self, tmp_path: Path) -> None:
        with (
            patch("providence_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch(
                "providence_cli.commands.init._find_blocking_parent_workspace",
                return_value=None,
            ),
        ):
            init(
                MagicMock(),
                type="client",
                name=None,
                force=False,
                no_bootstrap=True,
                default=False,
                language=None,
                list_commands=False,
            )
        content = (tmp_path / ".providence" / "profile").read_text(encoding="utf-8")
        assert "client" in content

    def test_blocks_nested_workspace(self, tmp_path: Path) -> None:
        """init inside an already-initialized workspace parent must fail."""
        parent_root = tmp_path / "parent"
        child = parent_root / "child"
        profile_path = parent_root / ".providence" / "profile"
        profile_path.parent.mkdir(parents=True)
        profile_path.write_text(
            "[sdd]\ntype = client\nname = client\nworkspace_id = ws-parent\n",
            encoding="utf-8",
        )
        with (
            pytest.raises(typer.Exit) as exc_info,
            patch("providence_cli.commands.init.Path.cwd", return_value=child),
            patch(
                "providence_cli.commands.init._find_blocking_parent_workspace",
                return_value=parent_root,
            ),
        ):
            # Simulate parent workspace detected
            init(
                MagicMock(),
                type="client",
                name=None,
                force=False,
                default=False,
                language=None,
                list_commands=False,
            )
        assert exc_info.value.exit_code == 1

    def test_allows_nested_init_when_parent_sdd_has_no_profile(
        self, tmp_path: Path
    ) -> None:
        """A bare `.providence/` ancestor with no profile (e.g. the global CLI
        toolchain cache under the user's home directory) must not block
        init — only a real initialized workspace should."""
        parent_root = tmp_path / "parent"
        child = parent_root / "child"
        (parent_root / ".providence" / "bin").mkdir(parents=True)
        with (
            patch("providence_cli.commands.init.Path.cwd", return_value=child),
            patch(
                "providence_cli.commands.init._find_blocking_parent_workspace",
                return_value=None,
            ),
        ):
            init(
                MagicMock(),
                type="client",
                name=None,
                force=False,
                no_bootstrap=True,
                default=False,
                language=None,
                list_commands=False,
            )
        assert (child / ".providence" / "profile").exists()
