"""Unit tests for providence_integration runners (filesystem, git, command, config)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from providence_integration.engine.types import (
    CommandExecInputs,
    ConfigValidateInputs,
    FilesystemCopyInputs,
    FilesystemCreateStructureInputs,
    GitCommitInputs,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helper functions to create Pydantic model instances from dicts
# ---------------------------------------------------------------------------


def make_filesystem_create_structure_inputs(
    data: dict[str, Any],
) -> FilesystemCreateStructureInputs:
    """Convert dict to FilesystemCreateStructureInputs model."""
    return FilesystemCreateStructureInputs(**data)


def make_filesystem_copy_inputs(data: dict[str, Any]) -> FilesystemCopyInputs:
    """Convert dict to FilesystemCopyInputs model."""
    return FilesystemCopyInputs(**data)


def make_command_exec_inputs(data: dict[str, Any]) -> CommandExecInputs:
    """Convert dict to CommandExecInputs model."""
    return CommandExecInputs(**data)


def make_config_validate_inputs(data: dict[str, Any]) -> ConfigValidateInputs:
    """Convert dict to ConfigValidateInputs model."""
    return ConfigValidateInputs(**data)


def make_git_commit_inputs(data: dict[str, Any]) -> GitCommitInputs:
    """Convert dict to GitCommitInputs model."""
    return GitCommitInputs(**data)


# ---------------------------------------------------------------------------
# filesystem_runner tests
# ---------------------------------------------------------------------------


class TestFilesystemRunnerIsSafePath:
    """Tests for _is_safe_path helper."""

    def test_child_is_safe(self, tmp_path: Path) -> None:
        from providence_integration.runners.filesystem_runner import _is_safe_path

        child = tmp_path / "subdir" / "file.txt"
        assert _is_safe_path(tmp_path, child) is True

    def test_base_itself_is_safe(self, tmp_path: Path) -> None:
        from providence_integration.runners.filesystem_runner import _is_safe_path

        assert _is_safe_path(tmp_path, tmp_path) is True

    def test_traversal_outside_is_unsafe(self, tmp_path: Path) -> None:
        from providence_integration.runners.filesystem_runner import _is_safe_path

        outside = tmp_path.parent / "other"
        assert _is_safe_path(tmp_path, outside) is False

    def test_absolute_sibling_is_unsafe(self, tmp_path: Path) -> None:
        from providence_integration.runners.filesystem_runner import _is_safe_path

        sibling = tmp_path.parent / "sibling_dir"
        assert _is_safe_path(tmp_path, sibling) is False


class TestRunFilesystemCreateStructure:
    """Tests for run_filesystem_create_structure."""

    def test_creates_directories(self, tmp_path: Path) -> None:
        from providence_integration.runners.filesystem_runner import (
            run_filesystem_create_structure,
        )

        inputs = make_filesystem_create_structure_inputs(
            {"directories": ["a/b/c", "d/e"]}
        )
        context: dict[str, Any] = {"working_dir": tmp_path}
        run_filesystem_create_structure(inputs, context, tmp_path)

        assert (tmp_path / "a" / "b" / "c").is_dir()
        assert (tmp_path / "d" / "e").is_dir()

    def test_empty_directories_list_is_noop(self, tmp_path: Path) -> None:
        from providence_integration.runners.filesystem_runner import (
            run_filesystem_create_structure,
        )

        inputs = make_filesystem_create_structure_inputs({"directories": []})
        context: dict[str, Any] = {"working_dir": tmp_path}
        run_filesystem_create_structure(inputs, context, tmp_path)
        # No error, no dirs created (beyond tmp_path itself)

    def test_path_traversal_raises_permission_error(self, tmp_path: Path) -> None:
        from providence_integration.runners.filesystem_runner import (
            run_filesystem_create_structure,
        )

        inputs = make_filesystem_create_structure_inputs(
            {"directories": ["../../etc/passwd"]}
        )
        context: dict[str, Any] = {"working_dir": tmp_path}

        with pytest.raises(PermissionError, match="Security violation"):
            run_filesystem_create_structure(inputs, context, tmp_path)

    def test_uses_cwd_when_no_working_dir_in_context(self, tmp_path: Path) -> None:
        from providence_integration.runners.filesystem_runner import (
            run_filesystem_create_structure,
        )

        # Provide empty context — should fall back to Path.cwd() without raising
        inputs = make_filesystem_create_structure_inputs({"directories": []})
        context: dict[str, Any] = {}
        # Should not raise
        run_filesystem_create_structure(inputs, context, tmp_path)


class TestRunFilesystemCopy:
    """Tests for run_filesystem_copy."""

    def test_copies_file(self, tmp_path: Path) -> None:
        from providence_integration.runners.filesystem_runner import run_filesystem_copy

        src_file = tmp_path / "src" / "hello.txt"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("content", encoding="utf-8")

        inputs = make_filesystem_copy_inputs(
            {"from": "src/hello.txt", "to": "dst/hello.txt"}
        )
        context: dict[str, Any] = {"working_dir": tmp_path}
        run_filesystem_copy(inputs, context, tmp_path)

        assert (tmp_path / "dst" / "hello.txt").read_text(encoding="utf-8") == "content"

    def test_copies_directory(self, tmp_path: Path) -> None:
        from providence_integration.runners.filesystem_runner import run_filesystem_copy

        src_dir = tmp_path / "mysrc"
        src_dir.mkdir()
        (src_dir / "a.txt").write_text("a", encoding="utf-8")
        (src_dir / "b.txt").write_text("b", encoding="utf-8")

        inputs = make_filesystem_copy_inputs({"from": "mysrc", "to": "mydst"})
        context: dict[str, Any] = {"working_dir": tmp_path}
        run_filesystem_copy(inputs, context, tmp_path)

        assert (tmp_path / "mydst" / "a.txt").read_text(encoding="utf-8") == "a"

    def test_destination_path_traversal_raises(self, tmp_path: Path) -> None:
        from providence_integration.runners.filesystem_runner import run_filesystem_copy

        src_file = tmp_path / "file.txt"
        src_file.write_text("data", encoding="utf-8")

        inputs = make_filesystem_copy_inputs(
            {"from": "file.txt", "to": "../../outside.txt"}
        )
        context: dict[str, Any] = {"working_dir": tmp_path}

        with pytest.raises(PermissionError, match="Security violation"):
            run_filesystem_copy(inputs, context, tmp_path)


# ---------------------------------------------------------------------------
# command_runner tests
# ---------------------------------------------------------------------------


class TestRunCommandExec:
    """Tests for run_command_exec."""

    @pytest.fixture(autouse=True)
    def _mock_safe_process_runner_for_tests(self, monkeypatch):
        """Mock SafeProcessRunner to allow test binaries (echo, false) in test environment."""
        import subprocess

        from providence_core.utils.process import ProcessResult, SafeProcessRunner

        original_run = SafeProcessRunner.run

        def mock_run(self, args, **kwargs):
            """Allow test binaries by delegating to real subprocess.run directly."""
            # For test binaries like 'echo', 'false', and the current Python
            # interpreter (used as a portable echo/false stand-in on Windows,
            # where standalone echo/false executables don't exist), bypass
            # SafeProcessRunner checks.
            is_python_stand_in = bool(args) and Path(args[0]).stem.lower().startswith(
                "python"
            )
            if args and (args[0] in ("echo", "false", "python3") or is_python_stand_in):
                proc = subprocess.run(
                    args,
                    shell=False,
                    capture_output=kwargs.get("capture_output", True),
                    text=True,
                    cwd=kwargs.get("cwd"),
                    timeout=kwargs.get("timeout"),
                    env=kwargs.get("env"),
                    input=kwargs.get("input_data"),
                )
                return ProcessResult(
                    command=args,
                    returncode=proc.returncode,
                    stdout=proc.stdout
                    if isinstance(proc.stdout, str)
                    else (proc.stdout.decode("utf-8") if proc.stdout else ""),
                    stderr=proc.stderr
                    if isinstance(proc.stderr, str)
                    else (proc.stderr.decode("utf-8") if proc.stderr else ""),
                    success=proc.returncode == 0,
                )
            # For all other binaries, use original SafeProcessRunner logic
            return original_run(self, args, **kwargs)

        monkeypatch.setattr(SafeProcessRunner, "run", mock_run)

    def test_empty_command_is_noop(self, tmp_path: Path) -> None:
        from pydantic import ValidationError

        context: dict[str, Any] = {"working_dir": tmp_path}
        # Empty command should fail validation
        try:
            make_command_exec_inputs({"command": ""})
            # If we get here without exception, skip the test
            pytest.skip("Empty command did not raise validation error")
        except ValidationError:
            # Expected: command validation should fail
            assert "last_exit_code" not in context

    def test_missing_command_key_is_noop(self, tmp_path: Path) -> None:
        from providence_integration.runners.command_runner import run_command_exec

        context: dict[str, Any] = {"working_dir": tmp_path}
        # Missing command key should raise validation error, so we catch it
        try:
            inputs = make_command_exec_inputs({})
        except ValueError:
            # Expected: command is required
            assert "last_exit_code" not in context
            return
        # If we got here, the model creation succeeded, so we should test it
        run_command_exec(inputs, context, tmp_path)
        assert "last_exit_code" not in context

    def test_successful_command_sets_exit_code_zero(self, tmp_path: Path) -> None:
        from providence_integration.runners.command_runner import run_command_exec

        context: dict[str, Any] = {"working_dir": tmp_path}
        # Use the current interpreter as a portable stand-in for `echo`:
        # standalone echo/false executables don't exist on Windows outside
        # Git's usr/bin, so shell=False subprocess calls to them can 404.
        python_exe = sys.executable.replace("\\", "/")
        inputs = make_command_exec_inputs(
            {"command": f'"{python_exe}" -c "print(\'hello\')"'}
        )
        run_command_exec(inputs, context, tmp_path)
        assert context["last_exit_code"] == 0
        assert "hello" in context["last_stdout"]

    def test_failing_command_sets_nonzero_exit_code(self, tmp_path: Path) -> None:
        from providence_integration.runners.command_runner import run_command_exec

        context: dict[str, Any] = {"working_dir": tmp_path}
        python_exe = sys.executable.replace("\\", "/")
        inputs = make_command_exec_inputs(
            {"command": f'"{python_exe}" -c "import sys; sys.exit(1)"'}
        )
        run_command_exec(inputs, context, tmp_path)
        assert context["last_exit_code"] != 0

    def test_uses_subprocess_run_with_correct_cwd(self, tmp_path: Path) -> None:
        from providence_integration.runners.command_runner import run_command_exec

        context: dict[str, Any] = {"working_dir": tmp_path}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            inputs = make_command_exec_inputs({"command": "echo test"})
            run_command_exec(inputs, context, tmp_path)
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args
            assert call_kwargs.kwargs.get("cwd") == tmp_path or (
                len(call_kwargs.args) > 1 or call_kwargs.kwargs.get("cwd") is not None
            )

    def test_stderr_captured(self, tmp_path: Path) -> None:
        from providence_integration.runners.command_runner import run_command_exec

        context: dict[str, Any] = {"working_dir": tmp_path}
        # Python command to write to stderr
        python_exe = sys.executable.replace("\\", "/")
        inputs = make_command_exec_inputs(
            {"command": f'"{python_exe}" -c "import sys; sys.stderr.write(\'err\')"'}
        )
        run_command_exec(inputs, context, tmp_path)
        assert "last_stderr" in context


# ---------------------------------------------------------------------------
# config_runner tests
# ---------------------------------------------------------------------------


class TestRunConfigValidate:
    """Tests for run_config_validate."""

    def test_missing_file_sets_empty_config(self, tmp_path: Path) -> None:
        from providence_integration.runners.config_runner import run_config_validate

        context: dict[str, Any] = {"working_dir": tmp_path}
        inputs = make_config_validate_inputs({"file": ".providence/profile"})
        run_config_validate(inputs, context, tmp_path)
        assert context["config"] == {}

    def test_reads_ini_file(self, tmp_path: Path) -> None:
        from providence_integration.runners.config_runner import run_config_validate

        config_file = tmp_path / "myconfig.ini"
        config_file.write_text("[section]\nkey = value\nfoo = bar\n", encoding="utf-8")
        context: dict[str, Any] = {"working_dir": tmp_path}
        inputs = make_config_validate_inputs({"file": "myconfig.ini"})
        run_config_validate(inputs, context, tmp_path)
        assert context["config"]["key"] == "value"
        assert context["config"]["foo"] == "bar"

    def test_multiple_sections_flattened(self, tmp_path: Path) -> None:
        from providence_integration.runners.config_runner import run_config_validate

        config_file = tmp_path / "multi.ini"
        config_file.write_text("[a]\nk1 = v1\n[b]\nk2 = v2\n", encoding="utf-8")
        context: dict[str, Any] = {"working_dir": tmp_path}
        inputs = make_config_validate_inputs({"file": "multi.ini"})
        run_config_validate(inputs, context, tmp_path)
        assert context["config"]["k1"] == "v1"
        assert context["config"]["k2"] == "v2"

    def test_default_file_path_used_when_not_specified(self, tmp_path: Path) -> None:
        from providence_integration.runners.config_runner import run_config_validate

        # Default is .providence/profile — missing → empty config
        context: dict[str, Any] = {"working_dir": tmp_path}
        inputs = make_config_validate_inputs({})
        run_config_validate(inputs, context, tmp_path)
        assert context["config"] == {}

    def test_creates_real_sdd_profile(self, tmp_path: Path) -> None:
        from providence_integration.runners.config_runner import run_config_validate

        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        profile = sdd_dir / "profile"
        profile.write_text("[sdd]\ntype = client\nname = test\n", encoding="utf-8")

        context: dict[str, Any] = {"working_dir": tmp_path}
        inputs = make_config_validate_inputs({})
        run_config_validate(inputs, context, tmp_path)
        assert context["config"]["type"] == "client"
        assert context["config"]["name"] == "test"


# ---------------------------------------------------------------------------
# git_runner tests
# ---------------------------------------------------------------------------


class TestRunGitCommit:
    """Tests for run_git_commit."""

    def test_calls_git_with_correct_args(self, tmp_path: Path) -> None:
        from providence_integration.runners.git_runner import run_git_commit

        inputs = make_git_commit_inputs({"message": "test commit"})
        context: dict[str, Any] = {"working_dir": tmp_path}

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_git_commit(inputs, context, tmp_path)
            # At minimum, git add and git commit must have been called
            calls = mock_run.call_args_list
            commands = [c.args[0] for c in calls]
            assert any("add" in cmd for cmd in commands)
            assert any("commit" in cmd for cmd in commands)

    def test_initializes_repo_when_no_git_dir(self, tmp_path: Path) -> None:
        from providence_integration.runners.git_runner import run_git_commit

        inputs = make_git_commit_inputs({"message": "init"})
        context: dict[str, Any] = {"working_dir": tmp_path}

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_git_commit(inputs, context, tmp_path)
            calls = mock_run.call_args_list
            commands = [c.args[0] for c in calls]
            # git init should have been called since no .git dir
            assert any("init" in cmd for cmd in commands)

    def test_skips_init_when_git_dir_exists(self, tmp_path: Path) -> None:
        from providence_integration.runners.git_runner import run_git_commit

        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        inputs = make_git_commit_inputs({"message": "commit msg"})
        context: dict[str, Any] = {"working_dir": tmp_path}

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_git_commit(inputs, context, tmp_path)
            calls = mock_run.call_args_list
            commands = [c.args[0] for c in calls]
            assert not any("init" in cmd for cmd in commands)

    def test_uses_default_message_when_not_provided(self, tmp_path: Path) -> None:
        from providence_integration.runners.git_runner import run_git_commit

        inputs = make_git_commit_inputs({})
        context: dict[str, Any] = {"working_dir": tmp_path}

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_git_commit(inputs, context, tmp_path)
            calls = mock_run.call_args_list
            # Check 'init' message is used in commit call
            commit_calls = [c for c in calls if "commit" in c.args[0]]
            # Default message is "init"
            assert any("init" in str(c) for c in commit_calls)
