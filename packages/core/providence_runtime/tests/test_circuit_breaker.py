"""Circuit breaker tests — Phase 3 budget enforcement.

Covers:
  - ContextLoader raises BudgetBreachError at utilization >= 100%
  - ContextLoader proceeds normally below 100%
  - BudgetBreachError carries utilization_pct and path_id
  - RetryBudget raises RetryCapReachedError at ceiling
  - RetryBudget.at_retry_ceiling() sentinel
  - ReflectionCapReachedError raised at reflection ceiling
  - PATH ceiling lookup (A=2, B=3, C=3, D=2 retries; A=1, B/C=2, D=1 reflections)
  - Unknown path_id falls back to most conservative ceiling (PATH A)
  - Count is not incremented when ceiling is reached (raise-before-mutate)
  - emit_event callback automatically emits economy.retry.cap.reached on ceiling
"""

from __future__ import annotations

from typing import Any

import pytest
from providence_runtime import (
    BudgetBreachError,
    ContextLoader,
    ContextRequest,
    ReflectionCapReachedError,
    RetryBudget,
    RetryCapReachedError,
)
from providence_runtime.budget import (
    _PATH_REFLECTION_CEILING,
    _PATH_RETRY_CEILING,
)

# ---------------------------------------------------------------------------
# BudgetBreachError — ContextLoader circuit breaker
# ---------------------------------------------------------------------------


class TestContextLoaderBreachBlock:
    def test_raises_on_exact_100_pct(self) -> None:
        req = ContextRequest(query="mandate", budget_utilization_pct=100.0)
        with pytest.raises(BudgetBreachError) as exc_info:
            ContextLoader().load_result(req)
        assert exc_info.value.utilization_pct == 100.0

    def test_raises_on_over_100_pct(self) -> None:
        req = ContextRequest(query="mandate", budget_utilization_pct=150.0)
        with pytest.raises(BudgetBreachError):
            ContextLoader().load_result(req)

    def test_load_shortcut_also_raises(self) -> None:
        req = ContextRequest(query="mandate", budget_utilization_pct=100.0)
        with pytest.raises(BudgetBreachError):
            ContextLoader().load(req)

    def test_proceeds_at_99_pct(self) -> None:
        req = ContextRequest(query="mandate", budget_utilization_pct=99.9)
        result = ContextLoader().load_result(req)
        # fallback stub returned — no breach
        assert result.source == "fallback"

    def test_proceeds_at_zero_pct(self) -> None:
        req = ContextRequest(query="mandate", budget_utilization_pct=0.0)
        result = ContextLoader().load_result(req)
        assert result.source == "fallback"

    def test_proceeds_when_pct_not_set(self) -> None:
        req = ContextRequest(query="mandate")
        result = ContextLoader().load_result(req)
        assert result.source == "fallback"

    def test_error_message_contains_utilization(self) -> None:
        req = ContextRequest(query="x", budget_utilization_pct=112.5)
        with pytest.raises(BudgetBreachError) as exc_info:
            ContextLoader().load_result(req)
        assert "112.5" in str(exc_info.value)

    def test_error_includes_path_id_when_provided(self) -> None:
        err = BudgetBreachError(utilization_pct=105.0, path_id="C")
        assert "PATH C" in str(err)
        assert err.path_id == "C"

    def test_error_without_path_id(self) -> None:
        err = BudgetBreachError(utilization_pct=100.0)
        assert err.path_id == ""
        assert "100.0" in str(err)


# ---------------------------------------------------------------------------
# PATH ceiling constants
# ---------------------------------------------------------------------------


class TestPathCeilings:
    def test_retry_ceiling_path_a(self) -> None:
        assert _PATH_RETRY_CEILING["A"] == 2

    def test_retry_ceiling_path_b(self) -> None:
        assert _PATH_RETRY_CEILING["B"] == 3

    def test_retry_ceiling_path_c(self) -> None:
        assert _PATH_RETRY_CEILING["C"] == 3

    def test_retry_ceiling_path_d(self) -> None:
        assert _PATH_RETRY_CEILING["D"] == 2

    def test_reflection_ceiling_path_a(self) -> None:
        assert _PATH_REFLECTION_CEILING["A"] == 1

    def test_reflection_ceiling_path_b(self) -> None:
        assert _PATH_REFLECTION_CEILING["B"] == 2

    def test_reflection_ceiling_path_c(self) -> None:
        assert _PATH_REFLECTION_CEILING["C"] == 2

    def test_reflection_ceiling_path_d(self) -> None:
        assert _PATH_REFLECTION_CEILING["D"] == 1


# ---------------------------------------------------------------------------
# RetryBudget — retry ceiling enforcement
# ---------------------------------------------------------------------------


class TestRetryBudget:
    def test_first_retry_succeeds(self) -> None:
        budget = RetryBudget(path_id="A")
        count = budget.increment_retry()
        assert count == 1
        assert budget.retry_count == 1

    def test_increments_sequentially(self) -> None:
        budget = RetryBudget(path_id="B")
        budget.increment_retry()
        budget.increment_retry()
        count = budget.increment_retry()
        assert count == 3
        assert budget.retry_count == 3

    def test_raises_at_ceiling_path_a(self) -> None:
        """PATH A ceiling = 2; third increment raises."""
        budget = RetryBudget(path_id="A")
        budget.increment_retry()
        budget.increment_retry()
        with pytest.raises(RetryCapReachedError) as exc_info:
            budget.increment_retry()
        assert exc_info.value.retry_count == 3
        assert exc_info.value.ceiling == 2
        assert exc_info.value.path_id == "A"

    def test_count_not_mutated_on_raise(self) -> None:
        """retry_count must remain at ceiling, not exceed it."""
        budget = RetryBudget(path_id="A")
        budget.increment_retry()
        budget.increment_retry()
        with pytest.raises(RetryCapReachedError):
            budget.increment_retry()
        assert budget.retry_count == 2  # NOT 3

    def test_raises_at_ceiling_path_b(self) -> None:
        """PATH B ceiling = 3; fourth increment raises."""
        budget = RetryBudget(path_id="B")
        for _ in range(3):
            budget.increment_retry()
        with pytest.raises(RetryCapReachedError):
            budget.increment_retry()

    def test_at_retry_ceiling_false_when_below(self) -> None:
        budget = RetryBudget(path_id="A")
        budget.increment_retry()
        assert not budget.at_retry_ceiling()

    def test_at_retry_ceiling_true_when_at_ceiling(self) -> None:
        budget = RetryBudget(path_id="A")
        budget.increment_retry()
        budget.increment_retry()
        assert budget.at_retry_ceiling()

    def test_unknown_path_uses_most_conservative_ceiling(self) -> None:
        """Unknown path_id → PATH A ceiling (most conservative = 2)."""
        budget = RetryBudget(path_id="Z")
        assert budget.retry_ceiling == _PATH_RETRY_CEILING["A"]

    def test_empty_path_id_uses_most_conservative_ceiling(self) -> None:
        budget = RetryBudget(path_id="")
        assert budget.retry_ceiling == _PATH_RETRY_CEILING["A"]

    def test_error_message_contains_path_id(self) -> None:
        err = RetryCapReachedError(retry_count=3, ceiling=2, path_id="A")
        assert "PATH A" in str(err)

    def test_initial_counts_are_zero(self) -> None:
        budget = RetryBudget(path_id="C")
        assert budget.retry_count == 0
        assert budget.reflection_count == 0

    def test_emit_event_callback_not_called_on_success(self) -> None:
        """When retry succeeds, emit_event callback should not be called."""
        events_emitted = []

        def capture_event(evt: Any) -> None:
            events_emitted.append(evt)

        budget = RetryBudget(path_id="A", emit_event=capture_event)
        budget.increment_retry()
        assert events_emitted == []

    def test_emit_event_callback_called_on_ceiling(self) -> None:
        """When retry ceiling is reached, emit_event callback is called."""
        events_emitted = []

        def capture_event(evt: Any) -> None:
            events_emitted.append(evt)

        budget = RetryBudget(path_id="A", emit_event=capture_event)
        budget.increment_retry()
        budget.increment_retry()
        with pytest.raises(RetryCapReachedError):
            budget.increment_retry()
        assert len(events_emitted) == 1

    def test_emitted_event_has_retry_cap_reached_name(self) -> None:
        """Emitted event must have event name = ECONOMY_RETRY_CAP_REACHED."""
        from providence_runtime.telemetry import ECONOMY_RETRY_CAP_REACHED

        events_emitted = []

        def capture_event(evt: Any) -> None:
            events_emitted.append(evt)

        budget = RetryBudget(path_id="A", emit_event=capture_event)
        budget.increment_retry()
        budget.increment_retry()
        with pytest.raises(RetryCapReachedError):
            budget.increment_retry()
        assert events_emitted[0].event == ECONOMY_RETRY_CAP_REACHED

    def test_emitted_event_carries_path_id(self) -> None:
        """Emitted event must include the path_id."""
        events_emitted = []

        def capture_event(evt: Any) -> None:
            events_emitted.append(evt)

        budget = RetryBudget(path_id="B", emit_event=capture_event)
        for _ in range(3):
            budget.increment_retry()
        with pytest.raises(RetryCapReachedError):
            budget.increment_retry()
        assert events_emitted[0].path_id == "B"

    def test_emitted_event_carries_ceiling_in_details(self) -> None:
        """Emitted event details must include the ceiling."""
        events_emitted = []

        def capture_event(evt: Any) -> None:
            events_emitted.append(evt)

        budget = RetryBudget(path_id="A", emit_event=capture_event)
        budget.increment_retry()
        budget.increment_retry()
        with pytest.raises(RetryCapReachedError):
            budget.increment_retry()
        assert events_emitted[0].details.get("ceiling") == 2  # PATH A ceiling


# ---------------------------------------------------------------------------
# RetryBudget — reflection ceiling enforcement
# ---------------------------------------------------------------------------


class TestReflectionBudget:
    def test_first_reflection_succeeds(self) -> None:
        budget = RetryBudget(path_id="A")
        count = budget.increment_reflection()
        assert count == 1

    def test_raises_at_reflection_ceiling_path_a(self) -> None:
        """PATH A ceiling = 1; second reflection raises."""
        budget = RetryBudget(path_id="A")
        budget.increment_reflection()
        with pytest.raises(ReflectionCapReachedError) as exc_info:
            budget.increment_reflection()
        assert exc_info.value.reflection_count == 2
        assert exc_info.value.ceiling == 1
        assert exc_info.value.path_id == "A"

    def test_reflection_count_not_mutated_on_raise(self) -> None:
        budget = RetryBudget(path_id="A")
        budget.increment_reflection()
        with pytest.raises(ReflectionCapReachedError):
            budget.increment_reflection()
        assert budget.reflection_count == 1  # NOT 2

    def test_raises_at_reflection_ceiling_path_b(self) -> None:
        """PATH B ceiling = 2; third reflection raises."""
        budget = RetryBudget(path_id="B")
        budget.increment_reflection()
        budget.increment_reflection()
        with pytest.raises(ReflectionCapReachedError):
            budget.increment_reflection()

    def test_at_reflection_ceiling_true_when_at_ceiling(self) -> None:
        budget = RetryBudget(path_id="A")
        budget.increment_reflection()
        assert budget.at_reflection_ceiling()

    def test_at_reflection_ceiling_false_when_below(self) -> None:
        budget = RetryBudget(path_id="B")
        budget.increment_reflection()
        assert not budget.at_reflection_ceiling()

    def test_retry_and_reflection_are_independent(self) -> None:
        """Exhausting retry ceiling does not affect reflection ceiling."""
        budget = RetryBudget(path_id="A")
        budget.increment_retry()
        budget.increment_retry()
        # retry is now at ceiling; reflection still has headroom
        assert budget.at_retry_ceiling()
        assert not budget.at_reflection_ceiling()
        count = budget.increment_reflection()
        assert count == 1
