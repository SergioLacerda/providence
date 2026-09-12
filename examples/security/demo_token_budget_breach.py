#!/usr/bin/env python3
"""
SDD Security Demo — Token Budget Breach

Shows SDD's circuit-breaker blocking an agent when its token consumption
exceeds the configured budget ceiling. Demonstrates the two-tier enforcement:
  - 90% utilization → WARN (degraded mode, continues)
  - 100%+ utilization → HARD BLOCK via TokenBudgetBreachError

Run from repo root:
    uv run python examples/security/demo_token_budget_breach.py
"""

from __future__ import annotations

from providence_runtime.budget import TokenBudget, TokenBudgetBreachError

SECTION = "\n" + "=" * 60


def simulate_agent_calls(budget: TokenBudget) -> None:
    """Simulate an agent making sequential LLM calls until the budget is breached."""
    calls = [
        ("claude-3-5-sonnet", 1500, 800, "reasoning"),
        ("claude-3-5-sonnet", 2000, 1200, "tool_call"),
        ("claude-3-5-sonnet", 1800, 950, "reflection"),
        ("claude-3-5-sonnet", 2500, 1400, "reasoning"),  # triggers WARN at ~90%
        ("claude-3-5-sonnet", 3000, 1600, "tool_call"),  # triggers BREACH at 100%+
    ]

    for i, (model, inp, out, category) in enumerate(calls, start=1):
        total_after = budget.consumed_tokens + inp + out
        utilization = (total_after / budget.max_tokens) * 100
        print(
            f"\n[Agent] Call {i}: model={model}  input={inp}  output={out}  category={category}"
        )
        print(f"[SDD]   Projected utilization: {utilization:.1f}% / 100%")

        try:
            budget.consume(model, inp, out, category=category)
            print(
                f"[SDD]   Allowed — tokens_total={budget.consumed_tokens}  "
                f"cost_usd=${budget.consumed_cost_usd:.4f}"
            )
        except TokenBudgetBreachError as exc:
            print(f"\n[SDD] TOKEN BUDGET BREACH on call {i}:")
            print(f"[SDD]   {exc}")
            print(f"[SDD]   Consumed : {exc.consumed:.0f} {exc.unit}")
            print(f"[SDD]   Limit    : {exc.limit:.0f} {exc.unit}")
            print("\n[SDD] Agent execution halted. Human checkpoint required.")
            return


def main() -> None:
    print(SECTION)
    print("SDD Security — Token Budget Breach Demo")
    print(SECTION)

    max_tokens = 10_000
    budget = TokenBudget(max_tokens=max_tokens, max_cost_usd=0.10)

    print(f"\n[SDD] Budget configured — max_tokens={max_tokens}  max_cost_usd=$0.10")
    print("[SDD] Circuit breaker: WARN at 90% | BLOCK at 100%")

    simulate_agent_calls(budget)
    print(SECTION)


if __name__ == "__main__":
    main()
