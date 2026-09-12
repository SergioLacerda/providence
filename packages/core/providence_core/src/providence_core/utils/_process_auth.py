"""Process authorization: binary allow-listing and argument validation."""

from __future__ import annotations

import logging
from pathlib import Path

from providence_core.utils._process_types import ProcessAuthorizationError

logger = logging.getLogger(__name__)

# Canonical list of binaries authorized for governed execution
AUTHORIZED_BINARIES: frozenset[str] = frozenset(
    {
        "openssl",
        "git",
        "ruff",
        "bandit",
        "mypy",
        "python",
        "python3",
        "pytest",
        "uv",
        "npm",
        "go",
        "docker",
        "bash",
        "golangci-lint",
        "cmd",
        "providence",
        "sdd",
        "sdd-compile",
    }
)


class ProcessAuthorizer:
    """Enforces binary allow-listing and argument safety rules."""

    def __init__(
        self, authorized_binaries: set[str] | frozenset[str] | None = None
    ) -> None:
        self._authorized = (
            frozenset(authorized_binaries)
            if authorized_binaries is not None
            else AUTHORIZED_BINARIES
        )

    def resolve_binary_name(self, binary: str) -> str:
        binary_name = Path(binary).name
        # Strip Windows executable suffixes (providence.exe -> providence, uv.exe -> uv, etc.).
        for suffix in (".exe", ".bat", ".cmd"):
            if binary_name.lower().endswith(suffix):
                binary_name = binary_name[: -len(suffix)]
                break
        # Release assets are platform-suffixed (for example
        # sdd-compile-linux-amd64) but represent the governed compiler binary.
        if binary_name.startswith("sdd-compile-"):
            return "sdd-compile"
        # Accept versioned python executable names (python3.11, python3.12, etc.).
        if binary_name.startswith("python"):
            return "python3"
        return binary_name

    def validate_python_args(self, binary_name: str, args: list[str]) -> None:
        """Validate Python arguments to prevent arbitrary code execution.

        Raises:
            ProcessAuthorizationError: If dangerous Python flags are detected.
        """
        if binary_name != "python3":
            return

        # Explicit contract:
        # - block arbitrary inline execution via python -c "<code>"
        # - allow module execution (-m), used by managed internal tooling
        # - narrowly allow "-m bandit ... -c <config-file>" for Bandit config files
        module_name = None
        for i, arg in enumerate(args[1:], start=1):
            if arg == "-m" and i + 1 < len(args):
                module_name = args[i + 1]
                break

        for i, arg in enumerate(args[1:], start=1):
            if arg != "-c":
                continue

            if module_name == "bandit":
                if i + 1 >= len(args):
                    raise ProcessAuthorizationError(
                        "Python flag '-c' requires a non-empty config file argument "
                        "when used with 'python -m bandit'."
                    )
                cfg = args[i + 1].strip()
                if not cfg:
                    raise ProcessAuthorizationError(
                        "Python flag '-c' requires a non-empty config file argument "
                        "when used with 'python -m bandit'."
                    )
                # Treat value as file path; reject obvious inline-code payloads.
                if any(ch in cfg for ch in ("\n", ";", "(", ")")):
                    raise ProcessAuthorizationError(
                        "Bandit '-c' argument must be a config file path."
                    )
                continue

            logger.error("Dangerous Python flag blocked: %s (arg %d)", arg, i)
            raise ProcessAuthorizationError(
                f"Python flag '{arg}' is not permitted for governed execution. "
                "Use a script path or an approved module execution pattern."
            )

    def validate_cmd_args(self, binary_name: str, args: list[str]) -> None:
        """Allow cmd.exe only for the Windows junction helper."""
        if binary_name != "cmd":
            return
        if (
            len(args) == 6
            and args[1].lower() == "/c"
            and args[2].lower() == "mklink"
            and args[3].lower() == "/j"
        ):
            return
        raise ProcessAuthorizationError(
            "cmd execution is only permitted for 'cmd /c mklink /J <link> <target>'."
        )

    def validate_args(self, args: list[str]) -> None:
        if not args:
            raise ProcessAuthorizationError("Command arguments cannot be empty")

        for i, arg in enumerate(args):
            if not isinstance(arg, str):
                raise ProcessAuthorizationError(
                    f"Argument {i} must be a string, got {type(arg).__name__}"
                )
            if "\x00" in arg:
                raise ProcessAuthorizationError(
                    f"Argument {i} contains null byte (NUL): {arg!r}"
                )
            if len(arg) > 65536:
                raise ProcessAuthorizationError(
                    f"Argument {i} exceeds maximum length (65536): {len(arg)} chars"
                )

    def authorize(self, args: list[str]) -> str:
        """Validate args and authorize the binary. Returns the resolved binary name."""
        binary_name = self.resolve_binary_name(args[0])
        if binary_name not in self._authorized:
            logger.error("Unauthorized binary execution attempt: %s", binary_name)
            raise ProcessAuthorizationError(
                f"Binary '{binary_name}' is not authorized for governed execution"
            )
        self.validate_python_args(binary_name, args)
        self.validate_cmd_args(binary_name, args)
        return binary_name
