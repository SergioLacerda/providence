"""Stabilization report aggregation and retryable-error classification."""

from __future__ import annotations

from typing import Any


def _parse_failure_lines(payload: Any, *, mode: str) -> list[str]:
    if not isinstance(payload, str):
        return []
    failures: list[str] = []
    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if mode == "lint":
            if "error" in lower or "warning" in lower or "failed" in lower:
                failures.append(line)
        elif mode == "test" and (
            lower.startswith("failed") or " failed" in lower or "error" in lower
        ):
            failures.append(line)
    return failures


def _build_stabilization_report(
    context: dict[str, Any], *, command_results: list[dict[str, Any]]
) -> dict[str, Any]:
    lint_summary = context.get("lint_summary", {})
    test_summary = context.get("test_summary", {})
    if not isinstance(lint_summary, dict):
        lint_summary = {}
    if not isinstance(test_summary, dict):
        test_summary = {}

    lint_failures: list[str] = []
    test_failures: list[str] = []
    critical_issues: list[str] = []

    for item in command_results:
        command = str(item.get("command", ""))
        status = str(item.get("status", "ok"))
        if status == "ok":
            continue
        if "lint" in command:
            lint_failures.append(command)
        elif "test" in command:
            test_failures.append(command)
        else:
            critical_issues.append(command)

    lint_failures.extend(
        [issue for issue in lint_summary.get("failures", []) if isinstance(issue, str)]
    )
    test_failures.extend(
        [issue for issue in test_summary.get("failures", []) if isinstance(issue, str)]
    )
    lint_failures.extend(_parse_failure_lines(context.get("lint_output"), mode="lint"))
    test_failures.extend(_parse_failure_lines(context.get("test_output"), mode="test"))
    critical_issues.extend(
        [
            issue
            for issue in context.get("critical_issues", [])
            if isinstance(issue, str)
        ]
        if isinstance(context.get("critical_issues", []), list)
        else []
    )

    if critical_issues or test_failures:
        decision = "block"
    elif lint_failures:
        decision = "warn"
    else:
        decision = "ready_to_ship"

    return {
        "decision": decision,
        "lint_failures": sorted(dict.fromkeys(lint_failures)),
        "test_failures": sorted(dict.fromkeys(test_failures)),
        "critical_issues": sorted(dict.fromkeys(critical_issues)),
        "escalation_needed": bool(critical_issues),
    }


def _is_retryable_error(*, exit_code: int, error: str) -> bool:
    if exit_code == 124:
        return True
    error_lower = error.lower()
    return any(
        marker in error_lower
        for marker in (
            "temporary",
            "temporarily",
            "timeout",
            "timed out",
            "rate limit",
            "try again",
        )
    )
