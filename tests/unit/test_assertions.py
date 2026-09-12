"""Unit tests for providence_integration assertions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# base.Assertion
# ---------------------------------------------------------------------------


class TestAssertion:
    def test_execute_raises_not_implemented(self) -> None:
        from providence_integration.assertions.base import Assertion

        a = Assertion(key="value")
        with pytest.raises(NotImplementedError):
            a.execute({})

    def test_params_stored(self) -> None:
        from providence_integration.assertions.base import Assertion

        a = Assertion(key="value", num=42)
        assert a.params["key"] == "value"
        assert a.params["num"] == 42


# ---------------------------------------------------------------------------
# filesystem.FsExistsAssertion
# ---------------------------------------------------------------------------


class TestFsExistsAssertion:
    def test_passes_when_file_exists(self, tmp_path: Path) -> None:
        from providence_integration.assertions.filesystem import FsExistsAssertion

        (tmp_path / "myfile.txt").write_text("content", encoding="utf-8")
        a = FsExistsAssertion(path="myfile.txt")
        result = a.execute({"working_dir": tmp_path})
        assert result.success is True
        assert "exists" in result.message

    def test_fails_when_file_missing(self, tmp_path: Path) -> None:
        from providence_integration.assertions.filesystem import FsExistsAssertion

        a = FsExistsAssertion(path="missing.txt")
        result = a.execute({"working_dir": tmp_path})
        assert result.success is False
        assert "NOT found" in result.message

    def test_works_with_nested_path(self, tmp_path: Path) -> None:
        from providence_integration.assertions.filesystem import FsExistsAssertion

        (tmp_path / "a" / "b").mkdir(parents=True)
        (tmp_path / "a" / "b" / "file.txt").write_text("x", encoding="utf-8")
        a = FsExistsAssertion(path="a/b/file.txt")
        result = a.execute({"working_dir": tmp_path})
        assert result.success is True

    def test_uses_cwd_when_no_working_dir(self, tmp_path: Path) -> None:
        from providence_integration.assertions.filesystem import FsExistsAssertion

        # Missing file, no context provided → uses cwd
        a = FsExistsAssertion(path="nonexistent_xyz_12345.txt")
        result = a.execute({})
        assert result.success is False


# ---------------------------------------------------------------------------
# git.GitHasCommitAssertion
# ---------------------------------------------------------------------------


class TestGitHasCommitAssertion:
    def test_passes_when_git_has_commit(self, tmp_path: Path) -> None:
        from providence_integration.assertions.git import GitHasCommitAssertion

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc1234def5678"

        a = GitHasCommitAssertion()
        with patch("subprocess.run", return_value=mock_result):
            result = a.execute({"working_dir": tmp_path})
        assert result.success is True

    def test_fails_when_no_commits(self, tmp_path: Path) -> None:
        from providence_integration.assertions.git import GitHasCommitAssertion

        mock_result = MagicMock()
        mock_result.returncode = 128

        a = GitHasCommitAssertion()
        with patch("subprocess.run", return_value=mock_result):
            result = a.execute({"working_dir": tmp_path})
        assert result.success is False
        assert "no commits" in result.message

    def test_fails_gracefully_when_git_not_found(self, tmp_path: Path) -> None:
        from providence_integration.assertions.git import GitHasCommitAssertion

        a = GitHasCommitAssertion()
        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            result = a.execute({"working_dir": tmp_path})
        assert result.success is False
        assert "git not found" in result.message


# ---------------------------------------------------------------------------
# config.ConfigHasKeyAssertion
# ---------------------------------------------------------------------------


class TestConfigHasKeyAssertion:
    def test_passes_when_key_present(self) -> None:
        from providence_integration.assertions.config import ConfigHasKeyAssertion

        a = ConfigHasKeyAssertion(key="my_key")
        result = a.execute({"config": {"my_key": "value"}})
        assert result.success is True
        assert "my_key" in result.message

    def test_fails_when_key_missing(self) -> None:
        from providence_integration.assertions.config import ConfigHasKeyAssertion

        a = ConfigHasKeyAssertion(key="missing_key")
        result = a.execute({"config": {}})
        assert result.success is False
        assert "missing" in result.message

    def test_fails_with_empty_config(self) -> None:
        from providence_integration.assertions.config import ConfigHasKeyAssertion

        a = ConfigHasKeyAssertion(key="any_key")
        result = a.execute({})
        assert result.success is False


# ---------------------------------------------------------------------------
# config.ConfigIsValidPathAssertion
# ---------------------------------------------------------------------------


class TestConfigIsValidPathAssertion:
    def test_passes_for_absolute_existing_path(self, tmp_path: Path) -> None:
        from providence_integration.assertions.config import ConfigIsValidPathAssertion

        a = ConfigIsValidPathAssertion(key="root_dir")
        result = a.execute(
            {
                "config": {"root_dir": str(tmp_path)},
                "working_dir": tmp_path,
            }
        )
        assert result.success is True

    def test_passes_for_relative_path_resolved_against_working_dir(
        self, tmp_path: Path
    ) -> None:
        from providence_integration.assertions.config import ConfigIsValidPathAssertion

        (tmp_path / "subdir").mkdir()
        a = ConfigIsValidPathAssertion(key="rel_dir")
        result = a.execute(
            {
                "config": {"rel_dir": "subdir"},
                "working_dir": tmp_path,
            }
        )
        assert result.success is True

    def test_fails_when_path_does_not_exist(self, tmp_path: Path) -> None:
        from providence_integration.assertions.config import ConfigIsValidPathAssertion

        a = ConfigIsValidPathAssertion(key="bad_path")
        result = a.execute(
            {
                "config": {"bad_path": str(tmp_path / "nonexistent")},
                "working_dir": tmp_path,
            }
        )
        assert result.success is False

    def test_fails_when_key_not_in_config(self, tmp_path: Path) -> None:
        from providence_integration.assertions.config import ConfigIsValidPathAssertion

        a = ConfigIsValidPathAssertion(key="missing_key")
        result = a.execute({"config": {}, "working_dir": tmp_path})
        assert result.success is False
        assert "not set" in result.message


# ---------------------------------------------------------------------------
# process.ProcessExitAssertion
# ---------------------------------------------------------------------------


class TestProcessExitAssertion:
    def test_passes_when_exit_code_matches(self) -> None:
        from providence_integration.assertions.process import ProcessExitAssertion

        a = ProcessExitAssertion(equals=0)
        result = a.execute({"last_exit_code": 0})
        assert result.success is True

    def test_fails_when_exit_code_differs(self) -> None:
        from providence_integration.assertions.process import ProcessExitAssertion

        a = ProcessExitAssertion(equals=0)
        result = a.execute({"last_exit_code": 1})
        assert result.success is False
        assert "expected 0, got 1" in result.message

    def test_fails_when_no_exit_code_in_context(self) -> None:
        from providence_integration.assertions.process import ProcessExitAssertion

        a = ProcessExitAssertion(equals=0)
        result = a.execute({})
        assert result.success is False


# ---------------------------------------------------------------------------
# process.ProcessNotAllSkippedAssertion
# ---------------------------------------------------------------------------


class TestProcessNotAllSkippedAssertion:
    def test_passes_when_no_pytest_summary(self) -> None:
        from providence_integration.assertions.process import (
            ProcessNotAllSkippedAssertion,
        )

        a = ProcessNotAllSkippedAssertion()
        result = a.execute({"last_stdout": "", "last_stderr": ""})
        assert result.success is True

    def test_passes_when_tests_passed(self) -> None:
        from providence_integration.assertions.process import (
            ProcessNotAllSkippedAssertion,
        )

        a = ProcessNotAllSkippedAssertion()
        result = a.execute({"last_stdout": "5 passed", "last_stderr": ""})
        assert result.success is True

    def test_fails_when_all_skipped(self) -> None:
        from providence_integration.assertions.process import (
            ProcessNotAllSkippedAssertion,
        )

        a = ProcessNotAllSkippedAssertion()
        result = a.execute({"last_stdout": "3 skipped", "last_stderr": ""})
        assert result.success is False
        assert "all tests skipped" in result.message

    def test_passes_when_some_passed_and_some_skipped(self) -> None:
        from providence_integration.assertions.process import (
            ProcessNotAllSkippedAssertion,
        )

        a = ProcessNotAllSkippedAssertion()
        result = a.execute({"last_stdout": "2 passed, 1 skipped", "last_stderr": ""})
        assert result.success is True

    def test_parse_pytest_summary_extracts_counts(self) -> None:
        from providence_integration.assertions.process import (
            ProcessNotAllSkippedAssertion,
        )

        a = ProcessNotAllSkippedAssertion()
        output = "5 passed, 2 failed, 1 error"
        counts = a._parse_pytest_summary(output)
        assert counts is not None
        assert counts["passed"] == 5
        assert counts["failed"] == 2
        assert counts["error"] == 1

    def test_parse_pytest_summary_returns_none_for_empty(self) -> None:
        from providence_integration.assertions.process import (
            ProcessNotAllSkippedAssertion,
        )

        a = ProcessNotAllSkippedAssertion()
        result = a._parse_pytest_summary("")
        assert result is None

    def test_parse_pytest_summary_normalizes_errors(self) -> None:
        from providence_integration.assertions.process import (
            ProcessNotAllSkippedAssertion,
        )

        a = ProcessNotAllSkippedAssertion()
        counts = a._parse_pytest_summary("3 errors")
        assert counts is not None
        assert counts["error"] == 3
