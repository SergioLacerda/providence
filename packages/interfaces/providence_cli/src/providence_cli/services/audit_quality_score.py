"""Audit quality-score computation: coerce raw signals, aggregate per-window score.

Split out of `audit_event_parser.py` (T14,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

from typing import Any


def _as_score(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int | float):
        return max(0.0, min(1.0, float(value)))
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "pass", "passed", "ok", "accepted", "yes"}:
            return 1.0
        if lowered in {"false", "fail", "failed", "rejected", "no"}:
            return 0.0
    return 0.0


def _quality_score(events: list[dict[str, Any]]) -> float | None:
    tests: list[float] = []
    acceptance: list[float] = []
    for event in events:
        details = event.get("details", {})
        if not isinstance(details, dict):
            continue
        if "tests_passed" in details:
            tests.append(_as_score(details.get("tests_passed")))
        if "human_accepted" in details:
            acceptance.append(_as_score(details.get("human_accepted")))
    if not tests and not acceptance:
        return None
    test_avg = (sum(tests) / len(tests)) if tests else 0.0
    acceptance_avg = (sum(acceptance) / len(acceptance)) if acceptance else 0.0
    return round((0.6 * test_avg + 0.4 * acceptance_avg) * 100.0, 2)


def _has_quality_signals(events: list[dict[str, Any]]) -> bool:
    for event in events:
        details = event.get("details", {})
        if not isinstance(details, dict):
            continue
        if "tests_passed" in details or "human_accepted" in details:
            return True
    return False
