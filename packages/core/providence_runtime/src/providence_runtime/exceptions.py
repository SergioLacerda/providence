"""Domain exception hierarchy for providence_runtime."""

from __future__ import annotations


class SddRuntimeError(RuntimeError):
    """Base class for all providence_runtime domain errors."""


class BudgetError(SddRuntimeError):
    """Base class for all budget-enforcement errors."""


class BudgetBreachError(BudgetError):
    """Raised when a context load is attempted after budget BREACH (≥ 100%).

    Callers MUST catch this exception and escalate to a human checkpoint.
    Further context loading is blocked until the session is reset or the
    budget is explicitly overridden (§economy/execution-budget.md §Circuit Breaker Rule 3).
    """

    def __init__(self, utilization_pct: float, path_id: str = "") -> None:
        self.utilization_pct = utilization_pct
        self.path_id = path_id
        path_info = f" (PATH {path_id})" if path_id else ""
        super().__init__(
            f"[SDD] Budget BREACH{path_info}: utilization={utilization_pct:.1f}% ≥ 100%. "
            "Context loading blocked — escalate to human checkpoint."
        )


class TokenBudgetBreachError(BudgetError):
    """Raised when the token or cost budget ceiling is exceeded.

    Distinct from :class:`BudgetBreachError` which signals context-load
    utilisation ≥ 100%.  This exception fires when the raw token count or
    USD cost surpasses the configured ceiling in TokenBudget.
    """

    def __init__(self, consumed: float, limit: float, unit: str = "tokens") -> None:
        self.consumed = consumed
        self.limit = limit
        self.unit = unit
        super().__init__(
            f"[SDD] Token budget BREACH: consumed {consumed:.4f} {unit} "
            f"> limit {limit:.4f} {unit} — escalate to human checkpoint."
        )


class RetryCapReachedError(BudgetError):
    """Raised when a retry would exceed the ceiling for the active PATH.

    Callers MUST:
    1. Emit ``economy.retry.cap.reached`` via ``TelemetrySink``
    2. For PATH A: abort the task and require human checkpoint
    3. For PATH B/C: emit the event and continue with a warning
    4. For PATH D: abort the thread and escalate
    """

    def __init__(self, retry_count: int, ceiling: int, path_id: str = "") -> None:
        self.retry_count = retry_count
        self.ceiling = ceiling
        self.path_id = path_id
        path_info = f" (PATH {path_id})" if path_id else ""
        super().__init__(
            f"[SDD] Retry ceiling reached{path_info}: "
            f"retry_count={retry_count} would exceed ceiling={ceiling}. "
            "Emit economy.retry.cap.reached and handle per PATH policy."
        )


class ReflectionCapReachedError(BudgetError):
    """Raised when a reflection cycle would exceed the ceiling for the active PATH.

    Callers MUST commit to the current decision without further reflection.
    """

    def __init__(self, reflection_count: int, ceiling: int, path_id: str = "") -> None:
        self.reflection_count = reflection_count
        self.ceiling = ceiling
        self.path_id = path_id
        path_info = f" (PATH {path_id})" if path_id else ""
        super().__init__(
            f"[SDD] Reflection ceiling reached{path_info}: "
            f"reflection_count={reflection_count} would exceed ceiling={ceiling}. "
            "Commit to current decision."
        )
