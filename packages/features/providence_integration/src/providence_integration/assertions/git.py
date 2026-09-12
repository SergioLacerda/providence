"""Git."""

from pathlib import Path

from providence_integration.assertions.base import Assertion
from providence_integration.assertions.result import AssertionResult
from providence_integration.engine.types import RuntimeContext


class GitHasCommitAssertion(Assertion):
    """GitHasCommitAssertion."""

    def execute(self, runtime_context: RuntimeContext) -> AssertionResult:
        """Execute."""
        from providence_core.utils.process import ProcessSpawnError, SafeProcessRunner

        working_dir = runtime_context.get("working_dir", Path.cwd())
        try:
            runner = SafeProcessRunner()
            result = runner.run(
                ["git", "rev-parse", "HEAD"],
                cwd=working_dir,
            )
            if result.success:
                return AssertionResult(True, "git has at least one commit")
            return AssertionResult(False, "no commits found in repository")
        except (FileNotFoundError, ProcessSpawnError):
            return AssertionResult(False, "git not found")
