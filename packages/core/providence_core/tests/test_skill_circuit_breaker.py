"""Tests for CircuitBreaker and CircuitBreakerRegistry."""

from __future__ import annotations

from providence_core.skill_circuit_breaker import (
    DEFAULT_OPEN_TTL_SECONDS,
    DEFAULT_THRESHOLD,
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitState,
)


class TestCircuitState:
    def test_enum_values(self) -> None:
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitBreakerDefaults:
    def test_starts_closed(self) -> None:
        cb = CircuitBreaker(skill_id="sdd-diagnose")
        assert cb.state == CircuitState.CLOSED

    def test_default_threshold(self) -> None:
        cb = CircuitBreaker(skill_id="x")
        assert cb.threshold == DEFAULT_THRESHOLD

    def test_default_ttl(self) -> None:
        cb = CircuitBreaker(skill_id="x")
        assert cb.open_ttl_seconds == DEFAULT_OPEN_TTL_SECONDS

    def test_allows_execution_when_closed(self) -> None:
        cb = CircuitBreaker(skill_id="x")
        assert cb.allows_execution() is True

    def test_is_open_when_closed_returns_false(self) -> None:
        cb = CircuitBreaker(skill_id="x")
        assert cb.is_open() is False


class TestCircuitBreakerFailures:
    def test_failure_below_threshold_stays_closed(self) -> None:
        cb = CircuitBreaker(skill_id="x", threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_failure_at_threshold_opens(self) -> None:
        cb = CircuitBreaker(skill_id="x", threshold=3)
        for _ in range(3):
            new_state = cb.record_failure()
        assert new_state == CircuitState.OPEN
        assert cb.state == CircuitState.OPEN

    def test_is_open_after_threshold(self) -> None:
        cb = CircuitBreaker(skill_id="x", threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open() is True

    def test_blocks_execution_when_open(self) -> None:
        cb = CircuitBreaker(skill_id="x", threshold=1)
        cb.record_failure()
        assert cb.allows_execution() is False

    def test_failure_in_half_open_reopens(self) -> None:
        cb = CircuitBreaker(skill_id="x", threshold=1, open_ttl_seconds=0)
        cb.record_failure()
        # Force internal state to half-open by manipulating _opened_at far in the past
        cb._state = CircuitState.HALF_OPEN
        result = cb.record_failure()
        assert result == CircuitState.OPEN
        assert cb._state == CircuitState.OPEN


class TestCircuitBreakerSuccess:
    def test_success_resets_to_closed(self) -> None:
        cb = CircuitBreaker(skill_id="x", threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_success_resets_failure_count(self) -> None:
        cb = CircuitBreaker(skill_id="x", threshold=5)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0

    def test_allows_execution_after_reset(self) -> None:
        cb = CircuitBreaker(skill_id="x", threshold=1)
        cb.record_failure()
        cb.record_success()
        assert cb.allows_execution() is True


class TestCircuitBreakerHalfOpen:
    def test_transitions_to_half_open_after_ttl(self) -> None:
        cb = CircuitBreaker(skill_id="x", threshold=1, open_ttl_seconds=0)
        cb.record_failure()
        # TTL=0 means immediately half-open
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_allows_execution(self) -> None:
        cb = CircuitBreaker(skill_id="x", threshold=1, open_ttl_seconds=0)
        cb.record_failure()
        assert cb.allows_execution() is True

    def test_open_state_not_half_open_yet(self) -> None:
        cb = CircuitBreaker(skill_id="x", threshold=1, open_ttl_seconds=9999)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allows_execution() is False


class TestCircuitBreakerAsDict:
    def test_as_dict_keys(self) -> None:
        cb = CircuitBreaker(skill_id="sdd-ask", threshold=5, open_ttl_seconds=120)
        d = cb.as_dict()
        assert d["skill_id"] == "sdd-ask"
        assert d["state"] == "closed"
        assert d["failure_count"] == 0
        assert d["threshold"] == 5
        assert d["open_ttl_seconds"] == 120

    def test_as_dict_reflects_open_state(self) -> None:
        cb = CircuitBreaker(skill_id="x", threshold=1)
        cb.record_failure()
        assert cb.as_dict()["state"] == "open"


class TestCircuitBreakerRegistry:
    def test_get_creates_new_breaker(self) -> None:
        reg = CircuitBreakerRegistry()
        cb = reg.get("sdd-diagnose")
        assert isinstance(cb, CircuitBreaker)
        assert cb.skill_id == "sdd-diagnose"

    def test_get_returns_same_instance(self) -> None:
        reg = CircuitBreakerRegistry()
        a = reg.get("x")
        b = reg.get("x")
        assert a is b

    def test_allows_execution_delegates(self) -> None:
        reg = CircuitBreakerRegistry()
        assert reg.allows_execution("new-skill") is True

    def test_record_success_resets(self) -> None:
        reg = CircuitBreakerRegistry(default_threshold=1)
        reg.record_failure("sdd-ask")
        assert reg.allows_execution("sdd-ask") is False
        reg.record_success("sdd-ask")
        assert reg.allows_execution("sdd-ask") is True

    def test_record_failure_returns_state(self) -> None:
        reg = CircuitBreakerRegistry(default_threshold=1)
        state = reg.record_failure("sdd-correct")
        assert state == CircuitState.OPEN

    def test_all_states_returns_string_map(self) -> None:
        reg = CircuitBreakerRegistry(default_threshold=1)
        reg.record_failure("sdd-diagnose")
        reg.get("sdd-converge")
        states = reg.all_states()
        assert states["sdd-diagnose"] == "open"
        assert states["sdd-converge"] == "closed"

    def test_registry_uses_custom_defaults(self) -> None:
        reg = CircuitBreakerRegistry(default_threshold=10, default_open_ttl_seconds=60)
        cb = reg.get("x")
        assert cb.threshold == 10
        assert cb.open_ttl_seconds == 60
