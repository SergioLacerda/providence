"""Budget enforcement — retry and reflection ceilings per PATH.

Implements the hard retry/reflection limits defined in
§economy/efficiency-policy.md.  Callers increment the budget tracker;
once the ceiling is reached the next increment raises an error.

When an ``emit_event`` callback is provided, the budget tracker automatically
emits ``economy.retry.cap.reached`` before raising the exception.

Usage example::

    from providence_runtime.budget import RetryBudget, RetryCapReachedError

    budget = RetryBudget(path_id="A")
    try:
        budget.increment_retry()
    except RetryCapReachedError as exc:
        # If emit_event was wired, event already emitted automatically
        raise typer.Exit(3) from exc

With event emission::

    def on_event(evt):
        sink.emit(evt)

    budget = RetryBudget(path_id="A", emit_event=on_event)
    try:
        budget.increment_retry()  # auto-emits on ceiling breach
    except RetryCapReachedError:
        pass
"""

from __future__ import annotations

from providence_runtime.exceptions import (
    ReflectionCapReachedError as ReflectionCapReachedError,
)
from providence_runtime.exceptions import (
    RetryCapReachedError as RetryCapReachedError,
)
from providence_runtime.exceptions import (
    TokenBudgetBreachError as TokenBudgetBreachError,
)

from ._retry_budget import (
    _PATH_REFLECTION_CEILING,
    _PATH_RETRY_CEILING,
    RetryBudget,
)
from ._token_budget import TokenBudget
from ._token_consumption import TokenConsumption

__all__ = [
    "_PATH_REFLECTION_CEILING",
    "_PATH_RETRY_CEILING",
    "ReflectionCapReachedError",
    "RetryBudget",
    "RetryCapReachedError",
    "TokenBudget",
    "TokenBudgetBreachError",
    "TokenConsumption",
]
