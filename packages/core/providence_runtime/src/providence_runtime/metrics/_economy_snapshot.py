"""Point-in-time snapshot of aggregated token economy metrics."""

from __future__ import annotations

from dataclasses import dataclass, field

from ._model_metrics import ModelMetrics


@dataclass
class EconomySnapshot:
    """Point-in-time snapshot of aggregated token economy metrics.

    Thread-safe snapshot captured from TokenEconomyCollector.snapshot().
    All fields are immutable after creation.
    """

    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_tokens_total: int = 0
    total_cost_usd: float = 0.0
    total_calls: int = 0
    budget_utilization_pct: float = 0.0
    warn_count: int = 0
    breach_count: int = 0
    retry_cap_count: int = 0
    per_model: dict[str, ModelMetrics] = field(default_factory=dict)
