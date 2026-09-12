"""Per-model token and cost accumulator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelMetrics:
    """Per-model token and cost accumulators."""

    tokens_input: int = 0
    tokens_output: int = 0
    tokens_total: int = 0
    cost_usd: float = 0.0
    call_count: int = 0
