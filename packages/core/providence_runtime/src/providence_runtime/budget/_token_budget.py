"""Hybrid token/USD budget tracker with circuit-breaker telemetry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from providence_runtime.exceptions import TokenBudgetBreachError

from ._token_consumption import TokenConsumption


class TokenBudget:
    """
    Hybrid budget tracker for tokens and USD costs.

    Pricing is based on per-model registry.
    """

    # Default pricing: (input_price_per_1k, output_price_per_1k)
    PRICING_REGISTRY = {
        "gpt-4o": (0.005, 0.015),
        "gpt-4o-mini": (0.00015, 0.0006),
        "claude-3-5-sonnet": (0.003, 0.015),
        "claude-3-7-sonnet": (0.003, 0.015),
        "claude-3-haiku": (0.00025, 0.00125),
        "gemini-2.0-flash": (0.0001, 0.0004),
        "gemini-2.0-pro": (0.00125, 0.005),
        "default": (0.01, 0.03),  # Conservative default
    }

    def __init__(
        self,
        max_tokens: int = 100000,
        max_cost_usd: float | None = None,
        emit_event: Callable[[Any], None] | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self.max_cost_usd = max_cost_usd
        self.emit_event = emit_event

        self.consumed_tokens = 0
        self.consumed_cost_usd = 0.0
        self.ledger: list[TokenConsumption] = []

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate USD cost for a given model and token count."""
        prices = self.PRICING_REGISTRY.get(model, self.PRICING_REGISTRY["default"])
        input_cost = (input_tokens / 1000.0) * prices[0]
        output_cost = (output_tokens / 1000.0) * prices[1]
        return input_cost + output_cost

    def consume(
        self, model: str, input_tokens: int, output_tokens: int, category: str = "other"
    ) -> TokenConsumption:
        """Record consumption and check against limits.

        Circuit breaker tiers:
        - 90%: WARN event, continues with degraded mode
        - 100%: HARD block via BudgetBreachError
        """
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        consumption = TokenConsumption(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            category=category,
            cost_usd=cost,
        )

        # Check limits before committing
        total_tokens = self.consumed_tokens + input_tokens + output_tokens
        total_cost = self.consumed_cost_usd + cost

        # WARN_THRESHOLD = 90% — degrade gracefully
        warn_threshold_tokens = self.max_tokens * 0.9
        if total_tokens > warn_threshold_tokens and total_tokens <= self.max_tokens:
            self._emit_warning("tokens", total_tokens, self.max_tokens)

        warn_threshold_cost = (
            self.max_cost_usd * 0.9 if self.max_cost_usd else float("inf")
        )
        if (
            self.max_cost_usd
            and total_cost > warn_threshold_cost
            and total_cost <= self.max_cost_usd
        ):
            self._emit_warning("usd", total_cost, self.max_cost_usd)

        # HARD_LIMIT = 100% — block immediately
        if total_tokens > self.max_tokens:
            self._emit_breach("tokens", total_tokens, self.max_tokens)
            raise TokenBudgetBreachError(total_tokens, self.max_tokens, "tokens")

        if self.max_cost_usd and total_cost > self.max_cost_usd:
            self._emit_breach("usd", total_cost, self.max_cost_usd)
            raise TokenBudgetBreachError(total_cost, self.max_cost_usd, "usd")

        # Commit
        self.ledger.append(consumption)
        self.consumed_tokens = total_tokens
        self.consumed_cost_usd = total_cost

        # Phase 0 fix: Emit economy.token.consume event for audit trail
        self._emit_consumption(consumption, total_tokens, total_cost)

        return consumption

    def _emit_consumption(
        self, consumption: TokenConsumption, total_tokens: int, total_cost_usd: float
    ) -> None:
        """Emit economy.token.consume event for audit trail (Phase 0 fix)."""
        if self.emit_event:
            import uuid

            from providence_runtime.telemetry import RuntimeEvent

            self.emit_event(
                RuntimeEvent(
                    event="economy.token.consume",
                    command="budget.consume",
                    status="ok",
                    trace_id=str(uuid.uuid4()),
                    tokens_input=consumption.input_tokens,
                    tokens_output=consumption.output_tokens,
                    tokens_total=consumption.input_tokens + consumption.output_tokens,
                    budget_utilization_pct=round(
                        (total_tokens / self.max_tokens) * 100, 2
                    )
                    if self.max_tokens > 0
                    else 0.0,
                    details={
                        "model": consumption.model,
                        "category": consumption.category,
                        "cost_usd": round(consumption.cost_usd, 4),
                        "total_cost_usd": round(total_cost_usd, 4),
                        "max_tokens": self.max_tokens,
                        "max_cost_usd": self.max_cost_usd,
                    },
                )
            )

    def _emit_warning(self, unit: str, consumed: float, limit: float) -> None:
        """Emit WARN event when budget utilization exceeds 90%."""
        if self.emit_event:
            import uuid

            from providence_runtime.telemetry import RuntimeEvent

            self.emit_event(
                RuntimeEvent(
                    event=f"economy.budget.warn.{unit}",
                    command="budget.consume",
                    status="warn",
                    trace_id=str(uuid.uuid4()),
                    details={
                        "consumed": consumed,
                        "limit": limit,
                        "utilization_pct": round((consumed / limit) * 100, 2),
                    },
                )
            )

    def _emit_breach(self, unit: str, consumed: float, limit: float) -> None:
        if self.emit_event:
            import uuid

            from providence_runtime.telemetry import RuntimeEvent

            self.emit_event(
                RuntimeEvent(
                    event=f"economy.budget.breach.{unit}",
                    command="budget.consume",
                    status="error",
                    trace_id=str(uuid.uuid4()),
                    details={"consumed": consumed, "limit": limit},
                )
            )

    def get_status(self) -> dict[str, Any]:
        """Return current budget status for telemetry or CLI."""
        return {
            "consumed_tokens": self.consumed_tokens,
            "max_tokens": self.max_tokens,
            "consumed_cost_usd": round(self.consumed_cost_usd, 4),
            "max_cost_usd": self.max_cost_usd,
            "usage_percent": round(
                (self.consumed_tokens / self.max_tokens) * 100
                if self.max_tokens > 0
                else 0,
                2,
            ),
            "transaction_count": len(self.ledger),
        }
