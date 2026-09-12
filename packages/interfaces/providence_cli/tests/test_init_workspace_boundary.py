"""Unit tests for providence_cli.commands.init_workspace_boundary."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from providence_cli.commands.init_workspace_boundary import (
    _find_blocking_parent_workspace,
    _find_parent_workspace_with_profile,
    _find_project_boundary,
    _is_relative_to,
)


def _write_profile(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[sdd]\ntype = client\n", encoding="utf-8")


class TestIsRelativeTo:
    def test_true_for_nested_path(self, tmp_path: Path) -> None:
        base = tmp_path / "base"
        child = base / "nested" / "deep"
        child.mkdir(parents=True)
        assert _is_relative_to(child, base) is True

    def test_false_for_unrelated_path(self, tmp_path: Path) -> None:
        base = tmp_path / "base"
        other = tmp_path / "other"
        base.mkdir()
        other.mkdir()
        assert _is_relative_to(base, other) is False


class TestFindProjectBoundary:
    def test_finds_marker_in_current_dir(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        (project / ".git").mkdir(parents=True)
        assert _find_project_boundary(project) == project

    def test_finds_marker_in_ancestor(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        nested = project / "src" / "pkg"
        nested.mkdir(parents=True)
        (project / "pyproject.toml").write_text("", encoding="utf-8")
        assert _find_project_boundary(nested) == project

    def test_returns_none_without_marker(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        assert _find_project_boundary(empty) is None


class TestFindParentWorkspaceWithProfile:
    def test_finds_ancestor_with_real_profile(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        _write_profile(home / ".providence" / "profile")
        deep = home / "dev" / "project"
        deep.mkdir(parents=True)
        assert _find_parent_workspace_with_profile(deep) == home

    def test_returns_none_without_any_profile(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        assert _find_parent_workspace_with_profile(deep) is None

    def test_ignores_bare_sdd_dir_without_profile_file(self, tmp_path: Path) -> None:
        """A bare `.providence/` (e.g. a toolchain cache) must not count as a workspace."""
        home = tmp_path / "home"
        (home / ".providence" / "bin").mkdir(parents=True)
        deep = home / "dev" / "project"
        deep.mkdir(parents=True)
        assert _find_parent_workspace_with_profile(deep) is None


class TestFindBlockingParentWorkspace:
    def test_none_when_no_ancestor_workspace(self, tmp_path: Path) -> None:
        cwd = tmp_path / "standalone"
        cwd.mkdir()
        assert _find_blocking_parent_workspace(cwd) is None

    def test_none_when_ancestor_sdd_dir_has_no_profile_file(
        self, tmp_path: Path
    ) -> None:
        """Defensive branch: even if a caller-supplied ancestor claims to have a
        profile, a missing real file on disk must not block init. Exercised via
        a direct patch since `_find_parent_workspace_with_profile` itself never
        returns a candidate without a real profile file  this guards against
        that invariant being violated by a future change."""
        home = tmp_path / "home"
        home.mkdir()
        cwd = home / "project"
        cwd.mkdir()
        with patch(
            "providence_cli.commands.init_workspace_boundary._find_parent_workspace_with_profile",
            return_value=home,
        ):
            assert _find_blocking_parent_workspace(cwd) is None

    def test_none_when_project_boundary_not_relative_to_workspace(
        self, tmp_path: Path
    ) -> None:
        """A real ancestor workspace exists, but the project's own boundary
        marker (.git) sits in a subtree the workspace is not an ancestor of
        relative to  e.g. the workspace is itself nested *inside* the
        project, not the other way around."""
        home = tmp_path / "home"
        _write_profile(home / ".providence" / "profile")
        project = home / "dev" / "project"
        (project / ".git").mkdir(parents=True)

        assert _find_blocking_parent_workspace(project) is None

    def test_returns_parent_workspace_when_blocking(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        _write_profile(home / ".providence" / "profile")
        cwd = home / "dev" / "project"
        cwd.mkdir(parents=True)

        assert _find_blocking_parent_workspace(cwd) == home
