"""StabilizeHandler — aggregate lint/test failures into a handoff report."""

from __future__ import annotations

from typing import Any

from .._base import Handler
from .._stabilization import _build_stabilization_report


class StabilizeHandler(Handler):
    """Aggregate lint/test failures into a handoff decision report.

    Example:
        Failing test commands yield `decision="block"` while lint-only issues
        yield `decision="warn"`.
    """

    def post_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        exit_code: int,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        del learning, exit_code
        command_results = artifacts.get("command_results", [])
        if not isinstance(command_results, list):
            command_results = []
        return {
            "stabilization_report": _build_stabilization_report(
                context, command_results=command_results
            )
        }
