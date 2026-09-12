"""Process runner types: exceptions, result dataclass, and output coercion."""

from __future__ import annotations

import subprocess  # nosec B404 — imported only for subprocess.TimeoutExpired base class, no process execution here
from dataclasses import dataclass


def _coerce_output(value: str | bytes | None) -> str:
    """Convert subprocess output into stable text without decode crashes."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")


class ProcessRunnerError(Exception):
    """Base error for governed process execution failures."""

    error_kind = "unknown"


class ProcessAuthorizationError(ValueError, ProcessRunnerError):
    """Raised when binary/arguments violate execution policy."""

    error_kind = "auth"


class ProcessSpawnError(ProcessRunnerError):
    """Raised when the process cannot be started."""

    error_kind = "spawn"


class ProcessTimeoutError(subprocess.TimeoutExpired, ProcessRunnerError):
    """Raised when process timeout is exceeded."""

    error_kind = "timeout"

    def __init__(self, cmd: list[str], timeout: float | None):
        super().__init__(cmd=cmd, timeout=timeout or 0)


class ProcessNonZeroExitError(ProcessRunnerError):
    """Raised when `check=True` and the process exits non-zero."""

    error_kind = "non_zero"


@dataclass(frozen=True)
class ProcessResult:
    """Result of a governed process execution."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    success: bool
    duration_ms: int = 0
    status: str = "unknown"
    error_kind: str | None = None
