"""Record of a single LLM token transaction."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class TokenConsumption:
    """Record of a single LLM token transaction."""

    input_tokens: int
    output_tokens: int
    model: str
    category: str  # 'reasoning' | 'tool_call' | 'reflection' | 'other'
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cost_usd: float = 0.0
