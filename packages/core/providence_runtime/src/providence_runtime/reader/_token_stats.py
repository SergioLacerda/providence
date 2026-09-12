"""Summary of token consumption across events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TokenStats:
    """Summary of token consumption across events."""

    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    event_count: int = 0
    unique_models: set[str] = None  # type: ignore
    cost_usd: float = 0.0
    avg_tokens_per_event: float = 0.0

    def __post_init__(self) -> None:
        if self.unique_models is None:
            self.unique_models = set()

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return {
            "total_tokens": self.total_tokens,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "event_count": self.event_count,
            "unique_models": sorted(self.unique_models),
            "cost_usd": round(self.cost_usd, 4),
            "avg_tokens_per_event": round(self.avg_tokens_per_event, 1),
        }
