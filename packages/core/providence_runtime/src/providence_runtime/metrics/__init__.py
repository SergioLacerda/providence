"""Token economy metrics aggregation and Prometheus text format exposition.

Zero-dependency: stdlib only. Thread-safe collectors for in-process token/cost
tracking and Prometheus text-format rendering (version 0.0.4).

Usage::

    from providence_runtime.metrics import TokenEconomyCollector, PrometheusTextRenderer
    from providence_runtime.reader import TelemetryReader
    from pathlib import Path

    # Replay JSONL to build metrics
    reader = TelemetryReader(Path(".providence/runtime/compliance-events.jsonl"))
    collector = TokenEconomyCollector.from_reader(reader)
    snap = collector.snapshot()

    # Render as Prometheus text format
    prometheus_text = PrometheusTextRenderer().render(snap)

    # Ingest live events
    collector.ingest(runtime_event)
"""

from __future__ import annotations

from ._ask_latency_collector import (
    AskLatencyCollector,
    AskLatencySnapshot,
    LatencyGroup,
)
from ._collector import TokenEconomyCollector
from ._config import _load_token_budget_config
from ._economy_snapshot import EconomySnapshot
from ._gate_latency_collector import (
    GateLatencyCollector,
    GateLatencyGroup,
    GateLatencySnapshot,
)
from ._model_metrics import ModelMetrics
from ._renderer import PrometheusTextRenderer

__all__ = [
    "AskLatencyCollector",
    "AskLatencySnapshot",
    "EconomySnapshot",
    "GateLatencyCollector",
    "GateLatencyGroup",
    "GateLatencySnapshot",
    "LatencyGroup",
    "ModelMetrics",
    "PrometheusTextRenderer",
    "TokenEconomyCollector",
    "_load_token_budget_config",
]
