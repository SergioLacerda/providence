import pytest
from providence_runtime.budget import (
    ReflectionCapReachedError,
    RetryBudget,
    RetryCapReachedError,
)


def test_retry_budget_increment_and_ceiling():
    budget = RetryBudget(path_id="B")
    assert budget.retry_ceiling == 3
    assert budget.retry_count == 0
    assert budget.increment_retry() == 1
    assert budget.increment_retry() == 2
    assert budget.increment_retry() == 3
    assert budget.at_retry_ceiling()
    with pytest.raises(RetryCapReachedError) as exc:
        budget.increment_retry()
    assert "ceiling" in str(exc.value)
    assert exc.value.retry_count == 4
    assert exc.value.ceiling == 3
    assert exc.value.path_id == "B"


def test_reflection_budget_increment_and_ceiling():
    budget = RetryBudget(path_id="C")
    assert budget.reflection_ceiling == 2
    assert budget.reflection_count == 0
    assert budget.increment_reflection() == 1
    assert budget.increment_reflection() == 2
    assert budget.at_reflection_ceiling()
    with pytest.raises(ReflectionCapReachedError) as exc:
        budget.increment_reflection()
    assert "ceiling" in str(exc.value)
    assert exc.value.reflection_count == 3
    assert exc.value.ceiling == 2
    assert exc.value.path_id == "C"


def test_default_path_is_conservative():
    budget = RetryBudget(path_id="Z")
    assert budget.retry_ceiling == 2  # PATH A default
    assert budget.reflection_ceiling == 1
    budget.increment_retry()
    budget.increment_retry()
    assert budget.at_retry_ceiling()
    with pytest.raises(RetryCapReachedError):
        budget.increment_retry()
    budget.increment_reflection()
    assert budget.at_reflection_ceiling()
    with pytest.raises(ReflectionCapReachedError):
        budget.increment_reflection()


def test_retry_budget_emit_event_called(monkeypatch):
    events = []

    def fake_emit(event):
        events.append(event)

    # Import the real telemetry module to patch the correct namespace
    import providence_runtime.telemetry as telemetry_mod

    class DummyEvent:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    monkeypatch.setattr(telemetry_mod, "RuntimeEvent", DummyEvent)
    monkeypatch.setattr(
        telemetry_mod, "ECONOMY_RETRY_CAP_REACHED", "economy.retry.cap.reached"
    )
    budget = RetryBudget(path_id="B", emit_event=fake_emit)
    budget.retry_count = budget.retry_ceiling  # set to ceiling
    with pytest.raises(RetryCapReachedError):
        budget.increment_retry()
    assert events, "emit_event should have been called"
    assert events[0].event == "economy.retry.cap.reached"
    assert events[0].path_id == "B"


def test_retry_budget_unknown_path_uses_conservative():
    budget = RetryBudget(path_id="UNKNOWN")
    assert budget.retry_ceiling == 2  # PATH A default
    assert budget.reflection_ceiling == 1
    budget.increment_retry()
    budget.increment_retry()
    assert budget.at_retry_ceiling()
    with pytest.raises(RetryCapReachedError):
        budget.increment_retry()
    budget.increment_reflection()
    assert budget.at_reflection_ceiling()
    with pytest.raises(ReflectionCapReachedError):
        budget.increment_reflection()


def test_retry_budget_ceiling_properties():
    budget = RetryBudget(path_id="C")
    assert not budget.at_retry_ceiling()
    budget.increment_retry()
    assert not budget.at_retry_ceiling()
    budget.increment_retry()
    budget.increment_retry()
    assert budget.at_retry_ceiling()
    budget = RetryBudget(path_id="D")
    assert not budget.at_reflection_ceiling()
    budget.increment_reflection()
    assert budget.at_reflection_ceiling()
