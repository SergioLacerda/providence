#!/usr/bin/env python3
"""
SDD Security Demo — Reflection Cap Reached

Shows SDD's RetryBudget cutting an agent stuck in a self-reflection loop.
Agents that repeatedly reflect on their own output without making progress
are a common runaway pattern; the reflection ceiling enforces a hard stop.

Ceilings per PATH (§economy/efficiency-policy.md):
  PATH A → 1 reflection max
  PATH B → 2 reflections max
  PATH C → 2 reflections max
  PATH D → 1 reflection max

Run from repo root:
    uv run python examples/security/demo_reflection_cap.py
"""

from __future__ import annotations

from providence_runtime.budget import RetryBudget
from providence_runtime.exceptions import ReflectionCapReachedError

SECTION = "\n" + "=" * 60


def simulate_reflection_loop(path_id: str) -> None:
    budget = RetryBudget(path_id=path_id)
    ceiling = budget.reflection_ceiling
    print(f"\n[Agent] Starting reflection loop on PATH {path_id}  (ceiling={ceiling})")

    reflection = 0
    while True:
        if budget.at_reflection_ceiling():
            try:
                budget.increment_reflection()
            except ReflectionCapReachedError as exc:
                print(f"[SDD]   Reflection {reflection + 1} BLOCKED — {exc}")
                print(
                    f"[SDD]   Cap reached at {reflection}/{ceiling}. Agent loop terminated."
                )
                return
        else:
            reflection = budget.increment_reflection()
            print(f"[Agent] Reflection {reflection} — re-evaluating response...")


def main() -> None:
    print(SECTION)
    print("SDD Security — Reflection Cap Demo")
    print(SECTION)
    print("\n[SDD] Simulating agents entering unbounded reflection loops...\n")

    for path_id in ("A", "B", "D"):
        simulate_reflection_loop(path_id)

    print(SECTION)


if __name__ == "__main__":
    main()
