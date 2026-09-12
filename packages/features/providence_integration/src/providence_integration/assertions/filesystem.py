"""Filesystem."""

from pathlib import Path

from providence_integration.engine.types import RuntimeContext

from .base import Assertion
from .result import AssertionResult


class FsExistsAssertion(Assertion):
    """FsExistsAssertion."""

    def execute(self, runtime_context: RuntimeContext) -> AssertionResult:
        """Execute."""
        working_dir = runtime_context.get("working_dir", Path.cwd())
        rel = self.param_str("path", default="")
        exists = (working_dir / rel).exists()

        if exists:
            return AssertionResult(True, f"{rel} exists")
        return AssertionResult(False, f"{rel} NOT found")
