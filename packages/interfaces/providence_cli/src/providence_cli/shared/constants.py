"""Canonical CLI constants for contract-first behavior."""

from pathlib import Path

EXIT_CODE_SUCCESS = 0
EXIT_CODE_CONTRACT_VIOLATION = 2
EXIT_CODE_OPERATIONAL_FAILURE = 3
BREACH_EXIT_CODE = EXIT_CODE_OPERATIONAL_FAILURE

LEARNING_WINDOW_DAYS = 7
TRUE_VALUES = {"1", "true", "yes", "on"}
RUNTIME_DIR = Path(".providence") / "runtime"
