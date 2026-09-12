import pytest
from providence_runtime.budget import (
    _PATH_REFLECTION_CEILING,
    _PATH_RETRY_CEILING,
    ReflectionCapReachedError,
    RetryBudget,
    RetryCapReachedError,
    TokenBudget,
    TokenBudgetBreachError,
)

pytestmark = pytest.mark.unit


# ============================================================================
# TokenBudget Tests
# ============================================================================


def test_token_budget_calculation():
    budget = TokenBudget()
    # gpt-4o: (0.005, 0.015) per 1k
    # 1000 input, 1000 output = 0.005 + 0.015 = 0.02
    cost = budget.calculate_cost("gpt-4o", 1000, 1000)
    assert cost == 0.02


def test_token_budget_consume():
    budget = TokenBudget(max_tokens=5000)
    consumption = budget.consume("gpt-4o", 1000, 1000, category="reasoning")

    assert budget.consumed_tokens == 2000
    assert budget.consumed_cost_usd == 0.02
    assert len(budget.ledger) == 1
    assert consumption.category == "reasoning"


def test_token_budget_breach_tokens():
    budget = TokenBudget(max_tokens=1000)
    with pytest.raises(TokenBudgetBreachError) as exc:
        budget.consume("gpt-4o", 600, 500)
    assert "consumed 1100.0000 tokens" in str(exc.value)
    assert "limit 1000.0000 tokens" in str(exc.value)


def test_token_budget_breach_usd():
    # Set a very low cost limit
    budget = TokenBudget(max_tokens=100000, max_cost_usd=0.01)
    with pytest.raises(TokenBudgetBreachError) as exc:
        budget.consume("gpt-4o", 1000, 1000)
    assert "consumed 0.0200 usd" in str(exc.value)
    assert "limit 0.0100 usd" in str(exc.value)


def test_token_budget_status():
    budget = TokenBudget(max_tokens=10000, max_cost_usd=1.0)
    budget.consume("gpt-4o", 1000, 1000)
    status = budget.get_status()

    assert status["consumed_tokens"] == 2000
    assert status["usage_percent"] == 20.0
    assert status["consumed_cost_usd"] == 0.02


def test_token_budget_multiple_calls():
    """Should accumulate consumption across multiple calls."""
    budget = TokenBudget(max_tokens=10000)
    budget.consume("gpt-4o", 500, 500)
    budget.consume("gpt-4o", 1000, 1000)

    assert budget.consumed_tokens == 3000
    assert len(budget.ledger) == 2


def test_token_budget_emits_consumption_event():
    """Should emit an economy.token.consume event when emit_event is configured."""
    events = []
    budget = TokenBudget(max_tokens=10000, emit_event=events.append)
    consumption = budget.consume("gpt-4o", 500, 500, category="reasoning")

    assert len(events) == 1
    event = events[0]
    assert event.event == "economy.token.consume"
    assert event.tokens_input == 500
    assert event.tokens_output == 500
    assert event.tokens_total == 1000
    assert event.details["model"] == "gpt-4o"
    assert event.details["category"] == "reasoning"
    assert event.details["cost_usd"] == round(consumption.cost_usd, 4)


def test_token_budget_emits_warning_event_near_token_limit():
    """Should emit economy.budget.warn.tokens when usage crosses the 90% threshold."""
    events = []
    budget = TokenBudget(max_tokens=1000, emit_event=events.append)
    budget.consume("gpt-4o", 600, 350)  # 950/1000 = 95%

    warn_events = [e for e in events if e.event == "economy.budget.warn.tokens"]
    assert len(warn_events) == 1
    assert warn_events[0].status == "warn"
    assert warn_events[0].details["consumed"] == 950
    assert warn_events[0].details["limit"] == 1000


def test_token_budget_emits_warning_event_near_cost_limit():
    """Should emit economy.budget.warn.usd when cost crosses the 90% threshold."""
    events = []
    budget = TokenBudget(max_tokens=100000, max_cost_usd=0.02, emit_event=events.append)
    budget.consume("gpt-4o", 1000, 900)  # cost = 0.0185 -> 92.5% of 0.02

    warn_events = [e for e in events if e.event == "economy.budget.warn.usd"]
    assert len(warn_events) == 1
    assert warn_events[0].status == "warn"
    assert warn_events[0].details["consumed"] == pytest.approx(0.0185)
    assert warn_events[0].details["limit"] == 0.02


def test_token_budget_emits_breach_event_on_token_breach():
    """Should emit economy.budget.breach.tokens before raising on a hard breach."""
    events = []
    budget = TokenBudget(max_tokens=1000, emit_event=events.append)

    with pytest.raises(TokenBudgetBreachError):
        budget.consume("gpt-4o", 600, 500)

    breach_events = [e for e in events if e.event == "economy.budget.breach.tokens"]
    assert len(breach_events) == 1
    assert breach_events[0].status == "error"
    assert breach_events[0].details["consumed"] == 1100
    assert breach_events[0].details["limit"] == 1000


# ============================================================================
# RetryBudget Tests
# ============================================================================


class TestRetryBudget:
    """Tests for retry and reflection budget tracking."""

    def test_retry_budget_path_a(self):
        """Should enforce retry ceiling for PATH A."""
        budget = RetryBudget(path_id="A")
        assert budget.retry_ceiling == _PATH_RETRY_CEILING["A"]

        # Should allow first increment
        result = budget.increment_retry()
        assert result == 1
        assert not budget.at_retry_ceiling()

        # Should allow increment up to ceiling
        result = budget.increment_retry()
        assert result == 2
        assert budget.at_retry_ceiling()

        # Should raise when exceeding ceiling
        with pytest.raises(RetryCapReachedError):
            budget.increment_retry()

    def test_retry_budget_path_b(self):
        """Should enforce retry ceiling for PATH B."""
        budget = RetryBudget(path_id="B")
        assert budget.retry_ceiling == _PATH_RETRY_CEILING["B"]

        # PATH B has higher ceiling
        budget.increment_retry()
        budget.increment_retry()
        budget.increment_retry()
        assert budget.at_retry_ceiling()

    def test_retry_budget_path_c(self):
        """Should enforce retry ceiling for PATH C."""
        budget = RetryBudget(path_id="C")
        assert budget.retry_ceiling == _PATH_RETRY_CEILING["C"]

    def test_retry_budget_path_d(self):
        """Should enforce retry ceiling for PATH D."""
        budget = RetryBudget(path_id="D")
        assert budget.retry_ceiling == _PATH_RETRY_CEILING["D"]

    def test_retry_budget_unset_path_id_defaults_to_a(self):
        """The common real-world case — no `SDD_PATH_ID` producer exists in
        production (CTX-05) — must keep silently defaulting to PATH A's
        conservative ceiling; this is unchanged, deliberate behavior."""
        budget = RetryBudget(path_id="")
        assert budget.retry_ceiling == _PATH_RETRY_CEILING["A"]
        assert budget.reflection_ceiling == _PATH_REFLECTION_CEILING["A"]

    def test_retry_budget_path_e_and_f_raise_instead_of_silently_using_a(self):
        """CTX-05 regression: PATH E and PATH F are recognized paths
        (§cognition/context-loading/path-routing.md) with no reviewed
        ceiling — silently reusing PATH A's ceiling for them would present
        an unreviewed policy gap as a real decision.
        `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` CTX-05.
        """
        for path_id in ("E", "F"):
            budget = RetryBudget(path_id=path_id)
            with pytest.raises(ValueError, match=path_id):
                _ = budget.retry_ceiling
            with pytest.raises(ValueError, match=path_id):
                _ = budget.reflection_ceiling

    def test_reflection_budget_path_a(self):
        """Should enforce reflection ceiling for PATH A."""
        budget = RetryBudget(path_id="A")
        assert budget.reflection_ceiling == _PATH_REFLECTION_CEILING["A"]  # Should be 1

        # PATH A has ceiling of 1, so first call should succeed
        result = budget.increment_reflection()
        assert result == 1

        # But second call should raise
        with pytest.raises(ReflectionCapReachedError):
            budget.increment_reflection()

    def test_reflection_budget_path_b(self):
        """Should enforce reflection ceiling for PATH B."""
        budget = RetryBudget(path_id="B")
        ceiling = budget.reflection_ceiling
        assert ceiling == _PATH_REFLECTION_CEILING["B"]

        # Should allow increments up to ceiling
        for _ in range(ceiling):
            budget.increment_reflection()

        # Should be at ceiling now
        assert budget.at_reflection_ceiling()

    def test_retry_budget_independent_paths(self):
        """Different paths should have independent budgets."""
        budget_a = RetryBudget(path_id="A")
        budget_b = RetryBudget(path_id="B")

        # PATH A has lower ceiling
        assert budget_a.retry_ceiling < budget_b.retry_ceiling

        # Incrementing one should not affect the other
        budget_a.increment_retry()
        budget_a.increment_retry()
        assert budget_a.at_retry_ceiling()
        assert not budget_b.at_retry_ceiling()

    def test_retry_cap_reached_error_attributes(self):
        """RetryCapReachedError should have accessible attributes."""
        error = RetryCapReachedError(retry_count=5, ceiling=3, path_id="A")
        assert error.retry_count == 5
        assert error.ceiling == 3
        assert error.path_id == "A"

    def test_reflection_cap_reached_error_attributes(self):
        """ReflectionCapReachedError should have accessible attributes."""
        error = ReflectionCapReachedError(reflection_count=2, ceiling=1, path_id="B")
        assert error.reflection_count == 2
        assert error.ceiling == 1
        assert error.path_id == "B"

    def test_all_paths_have_ceilings(self):
        """All PATH constants should be defined."""
        for path_id in ["A", "B", "C", "D"]:
            assert path_id in _PATH_RETRY_CEILING
            assert path_id in _PATH_REFLECTION_CEILING
            assert _PATH_RETRY_CEILING[path_id] > 0
            assert _PATH_REFLECTION_CEILING[path_id] > 0


class TestErrorHierarchy:
    """Verify unified error hierarchy from providence_runtime.exceptions."""

    def test_token_budget_breach_is_budget_error(self) -> None:
        from providence_runtime.exceptions import BudgetError, TokenBudgetBreachError

        assert issubclass(TokenBudgetBreachError, BudgetError)

    def test_retry_cap_reached_is_budget_error(self) -> None:
        from providence_runtime.exceptions import BudgetError, RetryCapReachedError

        assert issubclass(RetryCapReachedError, BudgetError)

    def test_budget_breach_is_providence_runtime_error(self) -> None:
        from providence_runtime.exceptions import BudgetBreachError, SddRuntimeError

        assert issubclass(BudgetBreachError, SddRuntimeError)

    def test_all_budget_errors_share_base(self) -> None:
        from providence_runtime.exceptions import (
            BudgetBreachError,
            BudgetError,
            ReflectionCapReachedError,
            RetryCapReachedError,
            TokenBudgetBreachError,
        )

        for cls in (
            BudgetBreachError,
            TokenBudgetBreachError,
            RetryCapReachedError,
            ReflectionCapReachedError,
        ):
            assert issubclass(cls, BudgetError), (
                f"{cls.__name__} should inherit from BudgetError"
            )
