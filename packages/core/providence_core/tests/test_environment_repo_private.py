from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

from providence_core.utils import _environment_repo as env_repo


def test_is_repo_root_true_and_false(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").touch()
    core = tmp_path / "packages" / "core" / "providence_core"
    core.mkdir(parents=True)
    (core / "pyproject.toml").touch()
    assert env_repo.is_repo_root(tmp_path) is True
    (core / "pyproject.toml").unlink()
    assert env_repo.is_repo_root(tmp_path) is False


def test_detect_repo_root_prefers_cwd(tmp_path: Path) -> None:
    with (
        patch.object(Path, "cwd", return_value=tmp_path),
        patch(
            "providence_core.utils._environment_repo.is_repo_root",
            side_effect=lambda p: p == tmp_path,
        ),
    ):
        assert env_repo.detect_repo_root() == tmp_path


def test_detect_repo_root_uses_file_parents_when_cwd_fails(tmp_path: Path) -> None:
    fake_file = tmp_path / "pkg" / "module.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("", encoding="utf-8")
    with (
        patch.object(Path, "cwd", return_value=tmp_path / "elsewhere"),
        patch(
            "providence_core.utils._environment_repo.is_repo_root",
            side_effect=lambda p: p == tmp_path,
        ),
        patch("providence_core.utils._environment_repo.__file__", str(fake_file)),
    ):
        assert env_repo.detect_repo_root() == tmp_path


def test_detect_repo_root_skips_file_fallback_when_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`allow_file_fallback=False` must raise instead of leaking whatever
    repo `__file__` physically lives in — the fix for the editable-install
    governance-content leak (see
    .analysis/pending/20260906-editable-install-leak-repro.md).

    `harness_like` and the fake cwd are siblings under `tmp_path` (neither
    is an ancestor of the other) so the cwd-parents search cannot
    accidentally find `harness_like` on its own — only the (disabled)
    file-fallback could.

    `GITHUB_WORKSPACE` is explicitly unset because the CI runner sets it
    for real whenever this suite runs inside providence's own GitHub
    Actions job — left unmocked, `detect_repo_root` would return that
    (legitimately correct, but irrelevant here) path via its separate
    `GITHUB_WORKSPACE` fallback instead of raising, masking this exact
    regression.
    """
    monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
    harness_like = tmp_path / "harness"
    fake_file = harness_like / "pkg" / "module.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("", encoding="utf-8")
    fake_cwd = tmp_path / "client" / "project"
    fake_cwd.mkdir(parents=True)
    with (
        patch.object(Path, "cwd", return_value=fake_cwd),
        patch(
            "providence_core.utils._environment_repo.is_repo_root",
            side_effect=lambda p: p == harness_like,
        ),
        patch("providence_core.utils._environment_repo.__file__", str(fake_file)),
        pytest.raises(RuntimeError, match="SDD Project root not found"),
    ):
        env_repo.detect_repo_root(allow_file_fallback=False)


def test_detect_repo_root_file_fallback_default_still_true(tmp_path: Path) -> None:
    """Backward compatibility: omitting the flag preserves the pre-fix
    behavior for the many self-hosted dev-tooling call sites that rely on
    it intentionally (e.g. `providence setup`, `providence test`)."""
    harness_like = tmp_path / "harness"
    fake_file = harness_like / "pkg" / "module.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("", encoding="utf-8")
    fake_cwd = tmp_path / "client" / "project"
    fake_cwd.mkdir(parents=True)
    with (
        patch.object(Path, "cwd", return_value=fake_cwd),
        patch(
            "providence_core.utils._environment_repo.is_repo_root",
            side_effect=lambda p: p == harness_like,
        ),
        patch("providence_core.utils._environment_repo.__file__", str(fake_file)),
    ):
        assert env_repo.detect_repo_root() == harness_like


def test_detect_repo_root_uses_github_workspace(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    with (
        patch(
            "providence_core.utils._environment_repo.is_repo_root", return_value=False
        ),
        patch.object(Path, "cwd", return_value=tmp_path / "nowhere"),
        patch(
            "providence_core.utils._environment_repo.__file__", str(tmp_path / "x.py")
        ),
    ):
        assert env_repo.detect_repo_root() == tmp_path.resolve()


def test_detect_repo_root_raises_when_not_found(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
    with (
        patch(
            "providence_core.utils._environment_repo.is_repo_root", return_value=False
        ),
        patch.object(Path, "cwd", return_value=tmp_path),
        patch(
            "providence_core.utils._environment_repo.__file__", str(tmp_path / "x.py")
        ),
        pytest.raises(RuntimeError, match="SDD Project root not found"),
    ):
        env_repo.detect_repo_root()


def test_get_project_config_handles_tomllib_absent(tmp_path: Path) -> None:
    with (
        patch(
            "providence_core.utils._environment_repo.detect_repo_root",
            return_value=tmp_path,
        ),
        patch("providence_core.utils._environment_repo.tomllib", None),
    ):
        assert env_repo.get_project_config() == {}


def test_get_project_config_reads_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='demo'\n", encoding="utf-8"
    )
    with patch(
        "providence_core.utils._environment_repo.detect_repo_root",
        return_value=tmp_path,
    ):
        config = env_repo.get_project_config()
    assert config["project"]["name"] == "demo"


def test_get_project_config_returns_empty_on_parse_error(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project\n", encoding="utf-8")
    with patch(
        "providence_core.utils._environment_repo.detect_repo_root",
        return_value=tmp_path,
    ):
        assert env_repo.get_project_config() == {}


def test_is_repo_root_returns_false_on_os_error(tmp_path: Path) -> None:
    with patch("pathlib.Path.exists", side_effect=OSError("denied")):
        assert env_repo.is_repo_root(tmp_path) is False


def test_detect_repo_root_handles_missing___file__(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
    monkeypatch.delattr(env_repo, "__file__", raising=False)
    with (
        patch.object(Path, "cwd", return_value=tmp_path),
        patch(
            "providence_core.utils._environment_repo.is_repo_root", return_value=False
        ),
        pytest.raises(RuntimeError, match="SDD Project root not found"),
    ):
        env_repo.detect_repo_root()


def test_detect_repo_root_returns_from___file___parents(tmp_path: Path) -> None:
    fake_file = tmp_path / "nested" / "pkg" / "module.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("", encoding="utf-8")
    with (
        patch.object(Path, "cwd", return_value=tmp_path / "cwd"),
        patch("providence_core.utils._environment_repo.__file__", str(fake_file)),
        patch(
            "providence_core.utils._environment_repo.is_repo_root",
            side_effect=lambda p: p == tmp_path,
        ),
    ):
        assert env_repo.detect_repo_root() == tmp_path


def test_module_import_sets_tomllib_none_when_both_backends_missing(
    tmp_path: Path,
) -> None:
    """`tomllib` and `tomli` are both attempted, in that order, via plain
    `try/except ImportError` (no `sys.version_info` branching — see
    `_environment_repo.py`, which must work correctly regardless of which
    interpreter version actually runs it, not just which version
    `[tool.mypy] python_version` claims)."""
    module_path = Path(env_repo.__file__)
    spec = importlib.util.spec_from_file_location(
        "test_env_repo_no_tomllib_or_tomli", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    original_import = builtins.__import__

    def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name in ("tomllib", "tomli"):
            raise ImportError(f"missing {name}")
        return original_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=_fake_import):
        spec.loader.exec_module(module)

    assert module.tomllib is None
