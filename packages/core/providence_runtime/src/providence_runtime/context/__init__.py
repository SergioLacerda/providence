"""Context loading engine — on-demand, budget-aware, artifact-backed."""

from __future__ import annotations

from providence_runtime.exceptions import BudgetBreachError as BudgetBreachError

from ._loader import ContextLoader
from ._matching import _match_items, _render_item
from ._request import ContextRequest
from ._result import ContextResult

__all__ = [
    "BudgetBreachError",
    "ContextLoader",
    "ContextRequest",
    "ContextResult",
    "_match_items",
    "_render_item",
]
