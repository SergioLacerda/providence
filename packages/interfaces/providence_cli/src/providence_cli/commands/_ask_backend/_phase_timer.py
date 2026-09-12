"""Phase timer helper for `providence ask` trace-route instrumentation.

Records wall-clock timing for named pipeline phases without changing the
behavior of the phases themselves. See
.analysis/refined/sdd-ask-traceroute-20260709/design.md for the event model
this feeds into.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PhaseRecord:
    """A single measured phase in an `providence ask` invocation."""

    phase_id: str
    latency_domain: str
    duration_ms: int
    start_ts: str
    end_ts: str
    measurement_quality: str = "measured"
    observed_by: str = "providence_cli"
    failed: bool = False
    # Soft-watchdog marker: True when duration_ms exceeded this phase's
    # configured threshold. Never affects control flow  see PhaseTimer.
    phase_slow: bool = False


@dataclass
class PhaseTimer:
    """Collects `PhaseRecord`s for the phases of one `providence ask` invocation.

    `thresholds_ms` / `default_threshold_ms` configure an optional,
    non-blocking watchdog (design.md 3): a phase whose measured
    `duration_ms` exceeds its threshold is marked `phase_slow=True` on its
    `PhaseRecord`  this never raises, never fails the command, and never
    changes timing behavior. Absent config (the default) disables the
    watchdog entirely; every record's `phase_slow` stays `False`.
    """

    _records: list[PhaseRecord] = field(default_factory=list)
    thresholds_ms: dict[str, int] = field(default_factory=dict)
    default_threshold_ms: int | None = None

    def threshold_for(self, phase_id: str) -> int | None:
        """The configured watchdog threshold for `phase_id`, if any."""
        return self.thresholds_ms.get(phase_id, self.default_threshold_ms)

    def _is_slow(self, phase_id: str, duration_ms: int) -> bool:
        threshold = self.threshold_for(phase_id)
        return threshold is not None and duration_ms > threshold

    @contextmanager
    def phase(
        self,
        phase_id: str,
        *,
        latency_domain: str,
        measurement_quality: str = "measured",
        observed_by: str = "providence_cli",
    ) -> Iterator[None]:
        start_mono = time.monotonic()
        start_ts = _utc_now_iso()
        failed = False
        try:
            yield
        except BaseException:
            failed = True
            raise
        finally:
            end_ts = _utc_now_iso()
            duration_ms = int((time.monotonic() - start_mono) * 1000)
            self._records.append(
                PhaseRecord(
                    phase_id=phase_id,
                    latency_domain=latency_domain,
                    duration_ms=duration_ms,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    measurement_quality=measurement_quality,
                    observed_by=observed_by,
                    failed=failed,
                    phase_slow=self._is_slow(phase_id, duration_ms),
                )
            )

    def record_external(
        self,
        phase_id: str,
        *,
        latency_domain: str,
        duration_ms: int,
        measurement_quality: str,
        observed_by: str,
    ) -> None:
        """Append a `PhaseRecord` for a phase that was not locally measured.

        Used for adapter/IDE-reported timings (e.g. external LLM exchange
        latency) that `providence_cli` cannot observe directly with `phase()`.
        """
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(milliseconds=duration_ms)
        self._records.append(
            PhaseRecord(
                phase_id=phase_id,
                latency_domain=latency_domain,
                duration_ms=duration_ms,
                start_ts=start_dt.isoformat(),
                end_ts=end_dt.isoformat(),
                measurement_quality=measurement_quality,
                observed_by=observed_by,
                failed=False,
                phase_slow=self._is_slow(phase_id, duration_ms),
            )
        )

    def records(self) -> list[PhaseRecord]:
        return list(self._records)

    def slow_records(self) -> list[PhaseRecord]:
        """Records whose duration exceeded their configured threshold."""
        return [r for r in self._records if r.phase_slow]

    def phase_total_ms(self) -> int:
        return sum(r.duration_ms for r in self._records)

    def unattributed_ms(self, *, session_duration_ms: int) -> int:
        return max(0, session_duration_ms - self.phase_total_ms())
