"""Thread-safe in-process accumulator for token economy RuntimeEvents."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from ._config import _load_token_budget_config
from ._economy_snapshot import EconomySnapshot
from ._model_metrics import ModelMetrics

if TYPE_CHECKING:
    from ..reader import TelemetryReader
    from ..telemetry import RuntimeEvent


class TokenEconomyCollector:
    """In-process accumulator for token economy RuntimeEvents.

    Thread-safe; uses a single RLock for all mutations.
    Can be populated from a TelemetryReader (JSONL replay) or
    by calling ingest(event) on each live RuntimeEvent.

    The collector filters and processes only relevant events:
      - economy.token.consume → increments token/cost counters and per-model tracking
      - economy.budget.warn* → increments warn_count
      - economy.budget.breach* → increments breach_count
      - economy.retry.cap.reached → increments retry_cap_count
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._snapshot = EconomySnapshot()
        self._budget_config = _load_token_budget_config()

    def ingest(self, event: RuntimeEvent | dict[str, Any]) -> None:
        """Update internal counters from a single RuntimeEvent or dict.

        No-op on irrelevant event types. Acquires lock for all mutations.

        Parameters
        ----------
        event:
            A RuntimeEvent or dict representation (e.g., from JSONL).
            Must have fields: event, tokens_input, tokens_output, tokens_total,
            budget_utilization_pct, details (dict).
        """
        # Normalize to dict interface
        event_dict = event.to_dict() if hasattr(event, "to_dict") else event

        event_type = event_dict.get("event", "")

        with self._lock:
            # Process economy.token.consume events
            if event_type == "economy.token.consume":
                tokens_in = event_dict.get("tokens_input") or 0
                tokens_out = event_dict.get("tokens_output") or 0
                tokens_tot = event_dict.get("tokens_total") or 0

                self._snapshot.total_tokens_input += tokens_in
                self._snapshot.total_tokens_output += tokens_out
                self._snapshot.total_tokens_total += tokens_tot
                self._snapshot.total_calls += 1

                # Track per-model metrics
                details = event_dict.get("details", {})
                if isinstance(details, dict):
                    model = details.get("model", "unknown")
                    cost = details.get("cost_usd", 0.0)

                    if model not in self._snapshot.per_model:
                        self._snapshot.per_model[model] = ModelMetrics()

                    m = self._snapshot.per_model[model]
                    m.tokens_input += tokens_in
                    m.tokens_output += tokens_out
                    m.tokens_total += tokens_tot
                    m.cost_usd += cost
                    m.call_count += 1

                    self._snapshot.total_cost_usd += cost

                # Calculate budget utilization percentage from config ceiling
                budget_ceiling = self._budget_config.get("token_budget_ceiling", 100000)
                if budget_ceiling > 0:
                    self._snapshot.budget_utilization_pct = (
                        self._snapshot.total_tokens_total / budget_ceiling
                    ) * 100
                else:
                    self._snapshot.budget_utilization_pct = 0.0

            # Process budget warn events
            elif event_type in (
                "economy.budget.warn",
                "economy.budget.warn.tokens",
                "economy.budget.warn.usd",
            ):
                self._snapshot.warn_count += 1

            # Process budget breach events
            elif event_type in (
                "economy.budget.breach",
                "economy.budget.breach.tokens",
                "economy.budget.breach.usd",
            ):
                self._snapshot.breach_count += 1

            # Process retry cap reached events
            elif event_type == "economy.retry.cap.reached":
                self._snapshot.retry_cap_count += 1

    @classmethod
    def from_reader(cls, reader: TelemetryReader) -> TokenEconomyCollector:
        """Build a collector by replaying all relevant events from a TelemetryReader.

        Iterates over all economy.token.consume, economy.budget.warn*, economy.budget.breach*,
        and economy.retry.cap.reached events and calls ingest() on each.

        Parameters
        ----------
        reader:
            An initialized TelemetryReader pointing to a JSONL events file.

        Returns
        -------
        TokenEconomyCollector with aggregated state from all events.
        """
        collector = cls()

        # Iterate all events and filter for relevant types
        for evt in reader.list_events():
            event_type = evt.get("event", "")
            if (
                event_type == "economy.token.consume"
                or event_type.startswith("economy.budget.warn")
                or event_type.startswith("economy.budget.breach")
                or event_type == "economy.retry.cap.reached"
            ):
                collector.ingest(evt)

        return collector

    def snapshot(self) -> EconomySnapshot:
        """Return a copy of the current aggregated state.

        Thread-safe; acquires lock for the entire copy operation.

        Returns
        -------
        EconomySnapshot with point-in-time values. Safe to share/serialize.
        """
        with self._lock:
            # Deep copy per_model dict
            per_model_copy = {
                model: ModelMetrics(
                    tokens_input=m.tokens_input,
                    tokens_output=m.tokens_output,
                    tokens_total=m.tokens_total,
                    cost_usd=m.cost_usd,
                    call_count=m.call_count,
                )
                for model, m in self._snapshot.per_model.items()
            }
            return EconomySnapshot(
                total_tokens_input=self._snapshot.total_tokens_input,
                total_tokens_output=self._snapshot.total_tokens_output,
                total_tokens_total=self._snapshot.total_tokens_total,
                total_cost_usd=self._snapshot.total_cost_usd,
                total_calls=self._snapshot.total_calls,
                budget_utilization_pct=self._snapshot.budget_utilization_pct,
                warn_count=self._snapshot.warn_count,
                breach_count=self._snapshot.breach_count,
                retry_cap_count=self._snapshot.retry_cap_count,
                per_model=per_model_copy,
            )

    def reset(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self._snapshot = EconomySnapshot()
