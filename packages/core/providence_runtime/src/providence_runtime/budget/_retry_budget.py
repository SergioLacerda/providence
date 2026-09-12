"""RetryBudget — retry/reflection ceilings per PATH for a single task."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from providence_runtime.exceptions import (
    ReflectionCapReachedError,
    RetryCapReachedError,
)

from ._token_budget import TokenBudget

# ---------------------------------------------------------------------------
# PATH ceilings (§economy/efficiency-policy.md)
# ---------------------------------------------------------------------------

_PATH_RETRY_CEILING: dict[str, int] = {
    "A": 2,
    "B": 3,
    "C": 3,
    "D": 2,
}

_PATH_REFLECTION_CEILING: dict[str, int] = {
    "A": 1,
    "B": 2,
    "C": 2,
    "D": 1,
}

# The canonical PATH taxonomy (§cognition/context-loading/path-routing.md)
# defines six paths, A-F, but only A-D have a reviewed retry/reflection
# ceiling. `SDD_PATH_ID` has no production producer today (CTX-05,
# `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`), so the
# unrecognized-path branch below (`path_id` empty or any other placeholder
# string) still safely defaults to PATH A's conservative ceiling — that
# behavior is unchanged. What changes is PATH E and PATH F specifically:
# an explicit path_id="E" or "F" is a real, named path with no defined
# budget yet, and silently treating it as PATH A would misrepresent an
# actual policy gap as a reviewed decision.
_RECOGNIZED_PATHS_WITHOUT_CEILING: frozenset[str] = frozenset({"E", "F"})


@dataclass
class RetryBudget:
    """Tracks retry and reflection counts for a single task execution.

    Also optionally holds a :class:`TokenBudget` for economic enforcement.
    """

    path_id: str = ""
    emit_event: Callable[[Any], None] | None = field(
        default=None, compare=False, repr=False
    )
    token_budget: TokenBudget | None = None
    retry_count: int = field(default=0, init=False)
    reflection_count: int = field(default=0, init=False)

    @property
    def retry_ceiling(self) -> int:
        """The retry ceiling for the active PATH.

        Raises `ValueError` for `path_id` "E" or "F" — recognized paths
        with no reviewed ceiling yet (CTX-05) — rather than silently
        reusing PATH A's. Any other unrecognized `path_id` (including the
        default `""`, since no production caller sets `SDD_PATH_ID` yet)
        still defaults to PATH A, unchanged.
        """
        if self.path_id in _RECOGNIZED_PATHS_WITHOUT_CEILING:
            raise ValueError(
                f"PATH {self.path_id!r} has no reviewed retry ceiling defined "
                "yet in _PATH_RETRY_CEILING (see CTX-05, "
                ".analysis/refined/20260906-gaps-e-melhorias-review/backlog.md)"
            )
        return _PATH_RETRY_CEILING.get(self.path_id, _PATH_RETRY_CEILING["A"])

    @property
    def reflection_ceiling(self) -> int:
        """The reflection ceiling for the active PATH.

        Same E/F policy as `retry_ceiling` above.
        """
        if self.path_id in _RECOGNIZED_PATHS_WITHOUT_CEILING:
            raise ValueError(
                f"PATH {self.path_id!r} has no reviewed reflection ceiling "
                "defined yet in _PATH_REFLECTION_CEILING (see CTX-05, "
                ".analysis/refined/20260906-gaps-e-melhorias-review/backlog.md)"
            )
        return _PATH_REFLECTION_CEILING.get(self.path_id, _PATH_REFLECTION_CEILING["A"])

    def increment_retry(self) -> int:
        """Increment retry count and return the new value."""
        next_count = self.retry_count + 1
        if next_count > self.retry_ceiling:
            # Auto-emit telemetry event if callback is wired
            if self.emit_event is not None:
                import uuid

                from providence_runtime.telemetry import (
                    ECONOMY_RETRY_CAP_REACHED,
                    RuntimeEvent,
                )

                event = RuntimeEvent(
                    event=ECONOMY_RETRY_CAP_REACHED,
                    command="retry.increment",
                    status="warn",
                    trace_id=str(uuid.uuid4()),
                    path_id=self.path_id,
                    retry_count=self.retry_count,
                    details={
                        "ceiling": self.retry_ceiling,
                        "would_be_count": next_count,
                    },
                )
                self.emit_event(event)
            raise RetryCapReachedError(
                retry_count=next_count,
                ceiling=self.retry_ceiling,
                path_id=self.path_id,
            )
        self.retry_count = next_count
        return self.retry_count

    def increment_reflection(self) -> int:
        """Increment reflection count and return the new value."""
        next_count = self.reflection_count + 1
        if next_count > self.reflection_ceiling:
            raise ReflectionCapReachedError(
                reflection_count=next_count,
                ceiling=self.reflection_ceiling,
                path_id=self.path_id,
            )
        self.reflection_count = next_count
        return self.reflection_count

    def at_retry_ceiling(self) -> bool:
        """Return True when the next retry would breach the ceiling."""
        return self.retry_count >= self.retry_ceiling

    def at_reflection_ceiling(self) -> bool:
        """Return True when the next reflection would breach the ceiling."""
        return self.reflection_count >= self.reflection_ceiling
