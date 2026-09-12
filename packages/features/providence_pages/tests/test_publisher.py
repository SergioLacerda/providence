"""Tests for providence_pages.publisher."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from providence_pages.publisher import GitHubPagesPublisher, PublishResult

pytestmark = pytest.mark.unit


class TestGitHubPagesPublisherValidate:
    def test_validate_returns_true_for_existing_dir(self, tmp_path: Path) -> None:
        publisher = GitHubPagesPublisher()
        assert publisher.validate(tmp_path) is True

    def test_validate_returns_false_for_missing_dir(self, tmp_path: Path) -> None:
        publisher = GitHubPagesPublisher()
        assert publisher.validate(tmp_path / "missing") is False

    def test_validate_returns_false_for_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "file.txt"
        file_path.write_text("x", encoding="utf-8")
        publisher = GitHubPagesPublisher()
        assert publisher.validate(file_path) is False


class TestGitHubPagesPublisherPublish:
    def test_publish_fails_when_source_missing(self, tmp_path: Path) -> None:
        publisher = GitHubPagesPublisher()
        result = publisher.publish(tmp_path / "missing")
        assert result.success is False
        assert "not found" in result.message

    def test_publish_success_calls_git_subtree(self, tmp_path: Path) -> None:
        publisher = GitHubPagesPublisher(remote="origin")
        with patch("providence_pages.publisher.SafeProcessRunner.run") as mock_run:
            mock_run.return_value = MagicMock(
                success=True, stdout="", stderr="", returncode=0
            )
            result = publisher.publish(tmp_path, branch="gh-pages")

        assert result.success is True
        assert result.branch == "gh-pages"
        call_args = mock_run.call_args[0][0]
        assert call_args[:3] == ["git", "subtree", "push"]
        assert "origin" in call_args
        assert "gh-pages" in call_args

    def test_publish_failure_captures_stderr(self, tmp_path: Path) -> None:
        publisher = GitHubPagesPublisher()
        with patch("providence_pages.publisher.SafeProcessRunner.run") as mock_run:
            mock_run.return_value = MagicMock(
                success=False, stdout="", stderr="fatal: error", returncode=1
            )
            result = publisher.publish(tmp_path)

        assert result.success is False
        assert "fatal: error" in result.message

    def test_publish_handles_missing_git_executable(self, tmp_path: Path) -> None:
        publisher = GitHubPagesPublisher()
        with patch(
            "providence_pages.publisher.SafeProcessRunner.run",
            side_effect=Exception("git executable not found"),
        ):
            result = publisher.publish(tmp_path)

        assert result.success is False
        assert "git executable not found" in result.message


class TestPublishResult:
    def test_default_message_is_empty(self) -> None:
        result = PublishResult(success=True, branch="gh-pages")
        assert result.message == ""
