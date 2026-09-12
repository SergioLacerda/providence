"""Process."""

import re

from providence_integration.assertions.base import Assertion
from providence_integration.assertions.result import AssertionResult
from providence_integration.engine.types import RuntimeContext


class ProcessExitAssertion(Assertion):
    """ProcessExitAssertion."""

    def execute(self, runtime_context: RuntimeContext) -> AssertionResult:
        """Execute."""
        expected = self._expected_exit_code()
        actual = runtime_context.get("last_exit_code")

        if actual == expected:
            return AssertionResult(True, "exit code ok")

        return AssertionResult(False, f"expected {expected}, got {actual}")

    def _expected_exit_code(self) -> int:
        return self.param_int("equals", default=0)


class ProcessNotAllSkippedAssertion(Assertion):
    """ProcessNotAllSkippedAssertion."""

    def execute(self, runtime_context: RuntimeContext) -> AssertionResult:
        """Execute."""
        output = "\n".join(
            [
                str(runtime_context.get("last_stdout", "") or ""),
                str(runtime_context.get("last_stderr", "") or ""),
            ]
        )

        summary = self._parse_pytest_summary(output)
        if summary is None:
            return AssertionResult(
                True, "pytest summary unavailable; skip guard not applied"
            )

        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        errors = summary.get("error", 0)
        skipped = summary.get("skipped", 0)

        if skipped > 0 and passed == 0 and failed == 0 and errors == 0:
            return AssertionResult(
                False, f"all tests skipped ({skipped}); compliance not verified"
            )

        return AssertionResult(True, "pytest executed non-skipped tests")

    def _parse_pytest_summary(self, output: str) -> dict[str, int] | None:
        if not output:
            return None

        counts: dict[str, int] = {}
        for number, label in re.findall(
            r"(\d+)\s+(passed|failed|error|errors|skipped|xfailed|xpassed)", output
        ):
            normalized = "error" if label == "errors" else label
            counts[normalized] = counts.get(normalized, 0) + int(number)

        return counts if counts else None
