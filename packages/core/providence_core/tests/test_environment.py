"""Unit tests for environment and path utilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from providence_core.utils.environment import (
    ProfileContext,
    WorkspaceNotInitializedError,
    detect_profile,
    detect_repo_root,
    find_workspace_root,
    get_profile_context,
    get_project_config,
    get_sdd_paths,
    is_repo_root,
    resolve_profile,
    resolve_venv_python,
    resolve_venv_sdd,
    write_profile,
)
from providence_core.utils.text_io import write_text_utf8

pytestmark = pytest.mark.unit


class TestFindWorkspaceRoot:
    """Tests for find_workspace_root (merged from tests/unit/test_environment.py)."""

    def test_returns_none_when_no_sdd_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A real ancestor of tmp_path (e.g. a cached ~/.providence/bin compiler
        # download) could otherwise leak in and make this test flaky, since
        # find_workspace_root walks all the way up to the filesystem root.
        monkeypatch.setattr(Path, "parents", property(lambda self: ()))
        result = find_workspace_root(start=tmp_path)
        assert result is None

    def test_finds_sdd_dir_in_start(self, tmp_path: Path) -> None:
        (tmp_path / ".providence").mkdir()
        result = find_workspace_root(start=tmp_path)
        assert result == tmp_path

    def test_finds_sdd_dir_in_parent(self, tmp_path: Path) -> None:
        (tmp_path / ".providence").mkdir()
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        result = find_workspace_root(start=nested)
        assert result == tmp_path


class TestResolveProfile:
    """Tests for resolve_profile (merged from tests/unit/test_environment.py)."""

    def test_override_master_returns_master_profile(self, tmp_path: Path) -> None:
        ctx = resolve_profile(root=tmp_path, override="master")
        assert ctx.type == "master"

    def test_override_client_returns_client_profile(self, tmp_path: Path) -> None:
        ctx = resolve_profile(root=tmp_path, override="client")
        assert ctx.type == "client"

    def test_env_var_override_takes_effect(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_PROFILE", "master")
        ctx = resolve_profile(root=tmp_path)
        assert ctx.type == "master"
        monkeypatch.delenv("SDD_PROFILE")

    def test_raises_when_no_sdd_dir_and_no_override(self, tmp_path: Path) -> None:
        with pytest.raises(WorkspaceNotInitializedError):
            resolve_profile(root=tmp_path)

    def test_reads_valid_profile_file(self, tmp_path: Path) -> None:
        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        profile_path = sdd_dir / "profile"
        write_text_utf8(
            profile_path,
            "[sdd]\ntype = master\nname = my-workspace\nworkspace_id = abc123\ncore_hash = ff00\n",
        )

        ctx = resolve_profile(root=tmp_path)
        assert ctx.type == "master"
        assert ctx.name == "my-workspace"
        assert ctx.workspace_id == "abc123"
        assert ctx.core_hash == "ff00"

    def test_raises_for_invalid_type_in_profile(self, tmp_path: Path) -> None:
        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        profile_path = sdd_dir / "profile"
        profile_path.write_text("[sdd]\ntype = unknown\n", encoding="utf-8")

        with pytest.raises(WorkspaceNotInitializedError):
            resolve_profile(root=tmp_path)


class TestWriteProfile:
    """Tests for write_profile (merged from tests/unit/test_environment.py)."""

    def test_writes_profile_file(self, tmp_path: Path) -> None:
        ctx = write_profile(tmp_path, "client", "test-workspace")
        profile_path = tmp_path / ".providence" / "profile"
        assert profile_path.exists()
        assert ctx.type == "client"
        assert ctx.name == "test-workspace"
        assert ctx.workspace_id != ""

    def test_creates_sdd_dir(self, tmp_path: Path) -> None:
        write_profile(tmp_path, "master", "master-ws")
        assert (tmp_path / ".providence").is_dir()

    def test_profile_is_readable_after_write(self, tmp_path: Path) -> None:
        write_profile(tmp_path, "client", "my-client")
        ctx = resolve_profile(root=tmp_path)
        assert ctx.type == "client"
        assert ctx.name == "my-client"

    def test_writes_and_reads_back_language(self, tmp_path: Path) -> None:
        ctx = write_profile(tmp_path, "client", "test-workspace", "pt-BR")
        assert ctx.language == "pt-BR"
        profile_text = (tmp_path / ".providence" / "profile").read_text(
            encoding="utf-8"
        )
        assert "language = pt-BR" in profile_text
        assert resolve_profile(root=tmp_path).language == "pt-BR"

    def test_no_language_key_when_not_passed(self, tmp_path: Path) -> None:
        ctx = write_profile(tmp_path, "client", "test-workspace")
        assert ctx.language is None
        profile_text = (tmp_path / ".providence" / "profile").read_text(
            encoding="utf-8"
        )
        assert "language" not in profile_text
        assert resolve_profile(root=tmp_path).language is None


class TestDetectProfile:
    """Tests for detect_profile backward-compat helper (merged)."""

    def test_returns_client_when_no_workspace(self, tmp_path: Path) -> None:
        result = detect_profile(root=tmp_path)
        assert result == "client"

    def test_returns_master_when_profile_is_master(self, tmp_path: Path) -> None:
        write_profile(tmp_path, "master", "m")
        result = detect_profile(root=tmp_path)
        assert result == "master"


class TestResolveVenvPython:
    """Tests for resolve_venv_python (merged from tests/unit/test_environment.py)."""

    def test_finds_linux_python(self, tmp_path: Path) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        python = bin_dir / "python"
        python.write_text("#!/bin/python", encoding="utf-8")

        result = resolve_venv_python(tmp_path)
        assert result == python

    def test_finds_windows_python(self, tmp_path: Path) -> None:
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        python_exe = scripts_dir / "python.exe"
        python_exe.write_text("exe", encoding="utf-8")

        result = resolve_venv_python(tmp_path)
        assert result == python_exe

    def test_raises_when_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeError, match="Could not find virtualenv python"):
            resolve_venv_python(tmp_path)


class TestResolveVenvSdd:
    """Tests for resolve_venv_sdd (merged from tests/unit/test_environment.py)."""

    def test_finds_linux_providence(self, tmp_path: Path) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        providence = bin_dir / "providence"
        providence.write_text("#!/bin/providence", encoding="utf-8")

        result = resolve_venv_sdd(tmp_path)
        assert result == providence

    def test_finds_windows_providence(self, tmp_path: Path) -> None:
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        providence_exe = scripts_dir / "providence.exe"
        providence_exe.write_text("exe", encoding="utf-8")

        result = resolve_venv_sdd(tmp_path)
        assert result == providence_exe

    def test_raises_when_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeError, match="Could not find providence executable"):
            resolve_venv_sdd(tmp_path)


class TestGetProfileContextDeprecated:
    """Tests for get_profile_context deprecated helper (merged)."""

    def test_returns_dict_with_required_keys(self) -> None:
        result = get_profile_context("client")
        assert "profile" in result
        assert "root" in result
        assert "paths" in result
        assert "is_master" in result
        assert "is_client" in result

    def test_client_profile_flags(self) -> None:
        result = get_profile_context("client")
        assert result["is_client"] is True
        assert result["is_master"] is False

    def test_master_profile_flags(self) -> None:
        result = get_profile_context("master")
        assert result["is_master"] is True
        assert result["is_client"] is False


class TestProfileContextImmutability:
    """Merged from tests/unit/test_environment.py TestProfileContext.test_frozen_immutable."""

    def test_frozen_immutable(self) -> None:
        ctx = ProfileContext(
            type="client",
            name="test",
            workspace_id="abc",
            core_hash="hash",
            root=Path("/tmp/workspace"),
        )
        with pytest.raises((AttributeError, TypeError)):
            ctx.name = "changed"


class TestIsRepoRoot:
    """Tests for is_repo_root detection."""

    def test_valid_repo_root(self, tmp_path: Path) -> None:
        """Should recognize valid repo root with required files."""
        (tmp_path / "pyproject.toml").touch()
        core_path = tmp_path / "packages" / "core" / "providence_core"
        core_path.mkdir(parents=True)
        (core_path / "pyproject.toml").touch()

        assert is_repo_root(tmp_path) is True

    def test_missing_root_pyproject(self, tmp_path: Path) -> None:
        """Should reject when root pyproject.toml missing."""
        core_path = tmp_path / "packages" / "core" / "providence_core"
        core_path.mkdir(parents=True)
        (core_path / "pyproject.toml").touch()

        assert is_repo_root(tmp_path) is False

    def test_missing_core_pyproject(self, tmp_path: Path) -> None:
        """Should reject when core pyproject.toml missing."""
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "packages" / "core" / "providence_core").mkdir(parents=True)

        assert is_repo_root(tmp_path) is False

    def test_handles_permission_errors(self, tmp_path: Path) -> None:
        """Should return False on permission errors."""
        with patch("pathlib.Path.exists", side_effect=PermissionError):
            assert is_repo_root(tmp_path) is False


class TestDetectRepoRoot:
    """Tests for repo root detection."""

    def test_detects_from_cwd(self, tmp_path: Path, monkeypatch) -> None:
        """Should detect repo root from current directory."""
        (tmp_path / "pyproject.toml").touch()
        core_path = tmp_path / "packages" / "core" / "providence_core"
        core_path.mkdir(parents=True)
        (core_path / "pyproject.toml").touch()

        monkeypatch.chdir(tmp_path)
        with patch("providence_core.utils.environment.is_repo_root", return_value=True):
            root = detect_repo_root()
            assert isinstance(root, Path)

    def test_detects_from_parent_directory(self, tmp_path: Path, monkeypatch) -> None:
        """Should detect repo root from parent directory."""
        (tmp_path / "pyproject.toml").touch()
        core_path = tmp_path / "packages" / "core" / "providence_core"
        core_path.mkdir(parents=True)
        (core_path / "pyproject.toml").touch()

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        with patch("providence_core.utils.environment.is_repo_root") as mock_is_root:
            mock_is_root.side_effect = lambda p: p == tmp_path
            root = detect_repo_root()
            assert root == tmp_path

    def test_detects_from_github_workspace(self, monkeypatch) -> None:
        """Should use GITHUB_WORKSPACE in CI environments."""
        gh_workspace = "/github/workspace"
        monkeypatch.setenv("GITHUB_WORKSPACE", gh_workspace)

        with patch(
            "providence_core.utils._environment_repo.is_repo_root", return_value=False
        ):
            root = detect_repo_root()
            assert root == Path(gh_workspace).resolve()

    def test_raises_when_not_found(self, monkeypatch) -> None:
        """Should raise when repo root cannot be found."""
        monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)

        with (
            patch(
                "providence_core.utils._environment_repo.is_repo_root",
                return_value=False,
            ),
            patch("pathlib.Path.parents", []),
            pytest.raises(RuntimeError, match="Project root not found"),
        ):
            detect_repo_root()


class TestProfileContext:
    """Tests for ProfileContext dataclass."""

    def test_profile_context_creation(self) -> None:
        """Should create ProfileContext with required fields."""
        ctx = ProfileContext(
            type="master",
            name="primary",
            workspace_id="ws-123",
            core_hash="abc123",
            root=Path("/tmp"),
        )
        assert ctx.type == "master"
        assert ctx.name == "primary"
        assert ctx.workspace_id == "ws-123"

    def test_is_master_property(self) -> None:
        """Should correctly identify master profile."""
        master_ctx = ProfileContext(
            type="master",
            name="master",
            workspace_id="ws-1",
            core_hash="hash1",
            root=Path("/tmp"),
        )
        assert master_ctx.is_master is True
        assert master_ctx.is_client is False

    def test_is_client_property(self) -> None:
        """Should correctly identify client profile."""
        client_ctx = ProfileContext(
            type="client",
            name="client",
            workspace_id="ws-2",
            core_hash="hash2",
            root=Path("/tmp"),
        )
        assert client_ctx.is_client is True
        assert client_ctx.is_master is False

    def test_as_dict_conversion(self) -> None:
        """Should convert ProfileContext to dict."""
        ctx = ProfileContext(
            type="master",
            name="test",
            workspace_id="ws-1",
            core_hash="hash",
            root=Path("/tmp"),
        )
        data = ctx.as_dict()
        assert data["profile"] == "master"
        assert data["name"] == "test"
        assert data["is_master"] is True


class TestGetProjectConfig:
    """Tests for project configuration loading."""

    def test_loads_pyproject_toml(self, tmp_path: Path) -> None:
        """Should load pyproject.toml when available."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test-project"\n', encoding="utf-8")

        with patch(
            "providence_core.utils._environment_repo.detect_repo_root",
            return_value=tmp_path,
        ):
            config = get_project_config()
            assert isinstance(config, dict)

    def test_returns_empty_dict_when_missing(self, tmp_path: Path) -> None:
        """Should return empty dict when pyproject.toml not found."""
        with patch(
            "providence_core.utils._environment_repo.detect_repo_root",
            return_value=tmp_path,
        ):
            config = get_project_config()
            assert config == {}

    def test_returns_empty_dict_on_parse_error(self, tmp_path: Path) -> None:
        """Should return empty dict on TOML parse errors."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("invalid toml content {{{", encoding="utf-8")

        with patch(
            "providence_core.utils._environment_repo.detect_repo_root",
            return_value=tmp_path,
        ):
            config = get_project_config()
            assert config == {}


class TestGetSddPaths:
    """Tests for SDD path resolution."""

    def test_returns_all_required_paths(self, tmp_path: Path) -> None:
        """Should return dict with all required paths."""
        (tmp_path / "generated").mkdir()

        with patch(
            "providence_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            paths = get_sdd_paths()

            required_keys = [
                "root",
                "master",
                "master_compiled",
                "master_build",
                "client",
                "client_compiled",
                "source_spec",
            ]
            for key in required_keys:
                assert key in paths
                assert isinstance(paths[key], Path)

    def test_root_path_is_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should set root path correctly."""
        (tmp_path / "generated").mkdir()
        monkeypatch.delenv("SDD_WORKSPACE_ROOT", raising=False)
        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=None,
            ),
            patch(
                "providence_core.utils.environment.detect_repo_root",
                return_value=tmp_path,
            ),
        ):
            paths = get_sdd_paths()
            assert paths["root"] == tmp_path

    def test_prefers_sdd_source_over_generated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should prefer .providence/source when it exists."""
        gen = tmp_path / "generated"
        gen.mkdir()
        monkeypatch.delenv("SDD_WORKSPACE_ROOT", raising=False)

        sdd_source = tmp_path / ".providence" / "source"
        sdd_source.mkdir(parents=True)

        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=None,
            ),
            patch(
                "providence_core.utils.environment.detect_repo_root",
                return_value=tmp_path,
            ),
        ):
            paths = get_sdd_paths()
            assert paths["source_spec"] == sdd_source

    def test_falls_back_to_workspace_root_when_repo_root_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should use workspace root when framework repo root is unavailable."""
        workspace_root = tmp_path / "client-project"
        (workspace_root / ".providence" / "source").mkdir(parents=True)
        monkeypatch.delenv("SDD_WORKSPACE_ROOT", raising=False)

        with (
            patch(
                "providence_core.utils.environment.detect_repo_root",
                side_effect=RuntimeError("repo root missing"),
            ),
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=workspace_root,
            ),
        ):
            paths = get_sdd_paths()
            assert paths["root"] == workspace_root
            assert paths["source_spec"] == workspace_root / ".providence" / "source"

    def test_falls_back_to_cwd_when_repo_and_workspace_missing(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Should use cwd for onboarding flows before `.providence` exists."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("SDD_WORKSPACE_ROOT", raising=False)

        with (
            patch(
                "providence_core.utils.environment.detect_repo_root",
                side_effect=RuntimeError("repo root missing"),
            ),
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=None,
            ),
        ):
            paths = get_sdd_paths()
            assert paths["root"] == tmp_path.resolve()
            assert (
                paths["source_spec"]
                == tmp_path / "generated" / "client" / "build" / "docs-meta"
            )

    def test_isolated_workspace_root_uses_env_generated_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should isolate generated artifacts under SDD_WORKSPACE_ROOT in tests."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        workspace_root = tmp_path / "shadow-workspace"
        monkeypatch.setenv("SDD_WORKSPACE_ROOT", str(workspace_root))

        with patch(
            "providence_core.utils.environment.detect_repo_root", return_value=repo_root
        ):
            paths = get_sdd_paths()
            assert paths["root"] == workspace_root.resolve()
            assert paths["repo_root"] == repo_root
            assert paths["generated"] == workspace_root / "generated"
            assert (
                paths["source_spec"]
                == workspace_root / "generated" / "client" / "build" / "docs-meta"
            )


class TestWorkspaceNotInitializedError:
    """Tests for workspace initialization error."""

    def test_error_message_includes_path(self) -> None:
        """Error message should include the start path."""
        start = Path("/tmp/test")
        error = WorkspaceNotInitializedError(start)

        assert str(start) in str(error)

    def test_error_suggests_sdd_init(self) -> None:
        """Error message should suggest running providence init."""
        error = WorkspaceNotInitializedError(Path("/tmp"))

        assert "providence init" in str(error)

    def test_error_suggests_profile_override(self) -> None:
        """Error message should mention --profile override."""
        error = WorkspaceNotInitializedError(Path("/tmp"))

        assert "--profile" in str(error) or "SDD_PROFILE" in str(error)
