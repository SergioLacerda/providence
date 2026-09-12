"""Current budget utilization snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BudgetStatus:
    """Current budget utilization snapshot."""

    max_tokens: int = 0
    consumed_tokens: int = 0
    utilization_pct: float = 0.0
    max_cost_usd: float | None = None
    consumed_cost_usd: float = 0.0
    warning_threshold_pct: float = 90.0
    breach_threshold_pct: float = 100.0
    in_red_zone: bool = False
    in_breach: bool = False

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return {
            "max_tokens": self.max_tokens,
            "consumed_tokens": self.consumed_tokens,
            "utilization_pct": self.utilization_pct,
            "max_cost_usd": self.max_cost_usd,
            "consumed_cost_usd": round(self.consumed_cost_usd, 4),
            "warning_threshold_pct": self.warning_threshold_pct,
            "breach_threshold_pct": self.breach_threshold_pct,
            "in_red_zone": self.in_red_zone,
            "in_breach": self.in_breach,
        }
