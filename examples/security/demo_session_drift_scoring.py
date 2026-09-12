#!/usr/bin/env python3
"""
SDD Security Demo — Session Drift Scoring (PATH Overload Detection)

Shows SDD's entropy-based drift scorer detecting when an agent is
systematically overloading complex PATHs (C/D) instead of decomposing
work. This is a governance signal — not a binary mismatch, but a
gradual drift score derived from session history.

PATHs defined in §economy/efficiency-policy.md:
  A = simple task (≤ 2 retries, ≤ 1 reflection)
  B = moderate task (≤ 3 retries, ≤ 2 reflections)
  C = complex feature (counted against overload threshold)
  D = multi-thread task (counted against overload threshold)

Overload condition: PATH C or D > 50% of all tasks.

Run from repo root:
    uv run python examples/security/demo_session_drift_scoring.py
"""

from __future__ import annotations

from providence_runtime import RuntimeEvent, SessionDriftScorer

SECTION = "\n" + "=" * 60


def make_event(path_id: str, command: str) -> RuntimeEvent:
    return RuntimeEvent(
        event="task.completed",
        command=command,
        status="ok",
        trace_id=f"trace-{command}-{path_id}",
        path_id=path_id,
    )


def print_distribution(label: str, events: list[RuntimeEvent]) -> None:
    dist = SessionDriftScorer.from_events(events)
    print(f"\n[SDD] --- {label} ---")
    print(f"[SDD] Total tasks     : {dist.total}")
    print(f"[SDD] PATH breakdown  : {dict(sorted(dist.counts.items()))}")
    print(f"[SDD] Dominant PATH   : {dist.dominant_path or '(none)'}")
    print(f"[SDD] Overloaded      : {dist.is_overloaded}")
    print(f"[SDD] Assessment      : {dist.reason}")
    if dist.is_overloaded:
        print("[SDD] ⚠ DRIFT DETECTED — agent scope too broad, decomposition required.")


def main() -> None:
    print(SECTION)
    print("SDD Security — Session Drift Scoring Demo")
    print(SECTION)
    print(
        "\n[SDD] Simulating three agent sessions with increasing PATH complexity...\n"
    )

    # Session 1: healthy — mostly simple and moderate tasks
    healthy_events = [
        make_event("A", "fix-typo"),
        make_event("A", "update-readme"),
        make_event("B", "add-endpoint"),
        make_event("A", "bump-version"),
        make_event("B", "refactor-module"),
        make_event("A", "patch-config"),
    ]
    print_distribution("Session 1 — Healthy (mostly A/B)", healthy_events)

    # Session 2: borderline — C tasks growing, not yet overloaded
    borderline_events = healthy_events + [
        make_event("C", "redesign-auth"),
        make_event("C", "migrate-schema"),
    ]
    print_distribution("Session 2 — Borderline (C growing)", borderline_events)

    # Session 3: overloaded — C tasks exceed 50% of all tasks
    overloaded_events = [
        make_event("C", "redesign-pipeline"),
        make_event("C", "rewrite-core-module"),
        make_event("C", "overhaul-api"),
        make_event("C", "refactor-entire-auth"),
        make_event("D", "multi-service-refactor"),
        make_event("A", "fix-lint"),
    ]
    print_distribution("Session 3 — OVERLOADED (C/D dominant)", overloaded_events)

    print(SECTION)


if __name__ == "__main__":
    main()
