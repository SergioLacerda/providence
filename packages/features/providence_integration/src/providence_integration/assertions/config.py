"""Config."""

from pathlib import Path

from providence_integration.assertions.base import Assertion
from providence_integration.assertions.result import AssertionResult
from providence_integration.engine.types import RuntimeContext


class ConfigHasKeyAssertion(Assertion):
    """ConfigHasKeyAssertion."""

    def execute(self, runtime_context: RuntimeContext) -> AssertionResult:
        """Execute."""
        config = runtime_context.get("config", {})
        key = self._key()

        if key in config:
            return AssertionResult(True, f"{key} found")

        return AssertionResult(False, f"{key} missing")

    def _key(self) -> str:
        return self.param_str("key", default="")


class ConfigIsValidPathAssertion(Assertion):
    """ConfigIsValidPathAssertion."""

    def execute(self, runtime_context: RuntimeContext) -> AssertionResult:
        """Execute."""
        config = runtime_context.get("config", {})
        key = self._key()
        value = config.get(key)
        working_dir = runtime_context.get("working_dir", Path.cwd())

        if not value:
            return AssertionResult(False, f"{key} not set")

        candidate = Path(str(value)).expanduser()
        if not candidate.is_absolute():
            candidate = (working_dir / candidate).resolve()

        if not candidate.exists():
            return AssertionResult(False, f"{key} path not found: {candidate}")

        return AssertionResult(True, f"{key} is a valid path: {candidate}")

    def _key(self) -> str:
        return self.param_str("key", default="")
