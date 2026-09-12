"""
Safe Process Runner - Governed system execution utility.

This module re-exports all public symbols for backward compatibility.
Implementation is split across focused submodules:
  _process_types.py        — exceptions + ProcessResult
  _process_auth.py          — ProcessAuthorizer + AUTHORIZED_BINARIES
  _process_runner.py        — SafeProcessRunner
  _process_module_check.py  — check_module_available
"""

from providence_core.utils._process_auth import AUTHORIZED_BINARIES, ProcessAuthorizer
from providence_core.utils._process_module_check import check_module_available
from providence_core.utils._process_runner import SafeProcessRunner
from providence_core.utils._process_types import (
    ProcessAuthorizationError,
    ProcessNonZeroExitError,
    ProcessResult,
    ProcessRunnerError,
    ProcessSpawnError,
    ProcessTimeoutError,
    _coerce_output,
)

__all__ = [
    "AUTHORIZED_BINARIES",
    "ProcessAuthorizationError",
    "ProcessAuthorizer",
    "ProcessNonZeroExitError",
    "ProcessResult",
    "ProcessRunnerError",
    "ProcessSpawnError",
    "ProcessTimeoutError",
    "SafeProcessRunner",
    "_coerce_output",
    "check_module_available",
]
