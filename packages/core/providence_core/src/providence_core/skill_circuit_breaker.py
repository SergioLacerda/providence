"""
Circuit breaker for skill execution.
Reference: skillsV6.md §4.3

Prevents repeated invocation of a failing skill.
States: closed (normal) → open (blocked) → half-open (probe) → closed.
All state transitions are deterministic given failure counts and timestamps.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Final

DEFAULT_THRESHOLD: Final[int] = 3
DEFAULT_OPEN_TTL_SECONDS: Final[int] = 300


class CircuitState(str, Enum):
    """CircuitState."""

    CLOSED = "closed"  # normal execution
    OPEN = "open"  # skill blocked; route to fallback
    HALF_OPEN = "half_open"  # one probe attempt allowed


@dataclass
class CircuitBreaker:
    """
    Per-skill circuit breaker.

    Thread-safety: not thread-safe. Use one instance per skill per request context.
    """

    skill_id: str
    threshold: int = DEFAULT_THRESHOLD
    open_ttl_seconds: int = DEFAULT_OPEN_TTL_SECONDS

    _failure_count: int = field(default=0, init=False, repr=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)
    _opened_at: float | None = field(default=None, init=False, repr=False)

    @property
    def state(self) -> CircuitState:
        """State."""
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            elapsed = time.time() - self._opened_at
            if elapsed >= self.open_ttl_seconds:
                return CircuitState.HALF_OPEN
        return self._state

    def is_open(self) -> bool:
        """Is Open."""
        return self.state == CircuitState.OPEN

    def allows_execution(self) -> bool:
        """Returns True if the skill may be called."""
        current = self.state
        return current in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Call after a successful skill execution."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._opened_at = None

    def record_failure(self) -> CircuitState:
        """
        Call after a failed skill execution.
        Returns the new state after recording the failure.
        """
        self._failure_count += 1

        if self._state == CircuitState.HALF_OPEN:
            # Probe failed — re-open immediately
            self._state = CircuitState.OPEN
            self._opened_at = time.time()
            return self._state

        if self._failure_count >= self.threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.time()

        return self._state

    def as_dict(self) -> dict[str, object]:
        """As Dict."""
        return {
            "skill_id": self.skill_id,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "threshold": self.threshold,
            "open_ttl_seconds": self.open_ttl_seconds,
        }


@dataclass
class CircuitBreakerRegistry:
    """
    Holds circuit breaker state for all skills in a session.
    Keyed by skill_id.
    """

    _breakers: dict[str, CircuitBreaker] = field(default_factory=dict)
    default_threshold: int = DEFAULT_THRESHOLD
    default_open_ttl_seconds: int = DEFAULT_OPEN_TTL_SECONDS

    def get(self, skill_id: str) -> CircuitBreaker:
        """Get."""
        if skill_id not in self._breakers:
            self._breakers[skill_id] = CircuitBreaker(
                skill_id=skill_id,
                threshold=self.default_threshold,
                open_ttl_seconds=self.default_open_ttl_seconds,
            )
        return self._breakers[skill_id]

    def allows_execution(self, skill_id: str) -> bool:
        """Allows Execution."""
        return self.get(skill_id).allows_execution()

    def record_success(self, skill_id: str) -> None:
        """Record Success."""
        self.get(skill_id).record_success()

    def record_failure(self, skill_id: str) -> CircuitState:
        """Record Failure."""
        return self.get(skill_id).record_failure()

    def all_states(self) -> dict[str, str]:
        """All States."""
        return {sid: cb.state.value for sid, cb in self._breakers.items()}
