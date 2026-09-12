"""Shared contracts and helpers for the rebuilt SDD CLI surface."""

from .constants import EXIT_CODE_CONTRACT_VIOLATION, EXIT_CODE_OPERATIONAL_FAILURE
from .contracts import CommandError, CommandResult, build_error_result, build_ok_result

__all__ = [
    "CommandError",
    "CommandResult",
    "EXIT_CODE_CONTRACT_VIOLATION",
    "EXIT_CODE_OPERATIONAL_FAILURE",
    "build_ok_result",
    "build_error_result",
]
