"""Tests for process type primitives: ProcessResult and exception hierarchy."""

from __future__ import annotations

import pytest

from providence_core.utils._process_types import (
    ProcessAuthorizationError,
    ProcessResult,
    ProcessRunnerError,
    ProcessSpawnError,
    ProcessTimeoutError,
)

pytestmark = pytest.mark.unit


class TestProcessResultDataclass:
    """Tests for ProcessResult dataclass."""

    def test_process_result_creation(self) -> None:
        """Should create ProcessResult with all fields."""
        result = ProcessResult(
            command=["git", "status"],
            returncode=0,
            stdout="output",
            stderr="",
            success=True,
        )
        assert result.returncode == 0
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.success is True

    def test_process_result_success(self) -> None:
        """returncode 0 indicates success."""
        result = ProcessResult(
            command=["git", "status"],
            returncode=0,
            stdout="",
            stderr="",
            success=True,
        )
        assert result.returncode == 0
        assert result.success is True

    def test_process_result_failure(self) -> None:
        """Non-zero returncode indicates failure."""
        result = ProcessResult(
            command=["git", "status"],
            returncode=1,
            stdout="",
            stderr="error",
            success=False,
        )
        assert result.returncode == 1
        assert result.success is False

    def test_process_result_is_frozen(self) -> None:
        """ProcessResult is immutable."""
        result = ProcessResult(
            command=["git", "status"],
            returncode=0,
            stdout="",
            stderr="",
            success=True,
        )
        with pytest.raises(AttributeError):
            result.returncode = 1  # type: ignore[misc]


class TestExceptionHierarchy:
    """Tests for the exception class hierarchy."""

    def test_authorization_error_is_value_error(self) -> None:
        assert issubclass(ProcessAuthorizationError, ValueError)

    def test_authorization_error_is_runner_error(self) -> None:
        assert issubclass(ProcessAuthorizationError, ProcessRunnerError)

    def test_spawn_error_is_runner_error(self) -> None:
        assert issubclass(ProcessSpawnError, ProcessRunnerError)

    def test_timeout_error_error_kind(self) -> None:
        err = ProcessTimeoutError(["git", "status"], 5.0)
        assert err.error_kind == "timeout"

    def test_timeout_error_zero_timeout_default(self) -> None:
        err = ProcessTimeoutError(["git"], None)
        assert err.timeout == 0
