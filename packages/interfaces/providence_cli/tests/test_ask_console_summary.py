"""Tests for the default-on `[SDD] <phase>  <Xs>` ask console summary."""

from __future__ import annotations

import time

from providence_cli.commands._ask_backend._phase_timer import PhaseTimer
from providence_cli.commands._ask_backend._pipeline_metrics import (
    print_ask_console_summary,
)


def test_prints_one_line_per_recorded_phase_plus_total(capsys) -> None:
    timer = PhaseTimer()
    with timer.phase("ask.workspace.resolve", latency_domain="local_fs"):
        time.sleep(0.01)
    with timer.phase("ask.governance.snapshot", latency_domain="governance"):
        time.sleep(0.01)
    entry_mono = time.monotonic() - 0.05

    print_ask_console_summary(timer, entry_mono=entry_mono)

    out = capsys.readouterr().out
    assert "[SDD] ask.workspace.resolve" in out
    assert "[SDD] ask.governance.snapshot" in out
    assert "[SDD] Total" in out
    # Total must come after the individual phase lines.
    assert out.index("Total") > out.index("ask.governance.snapshot")


def test_omits_zero_duration_phases(capsys) -> None:
    timer = PhaseTimer()
    with timer.phase("ask.budget.guard", latency_domain="governance"):
        pass  # near-instant; likely records duration_ms == 0
    entry_mono = time.monotonic()

    print_ask_console_summary(timer, entry_mono=entry_mono)

    out = capsys.readouterr().out
    if timer.records()[0].duration_ms == 0:
        assert "ask.budget.guard" not in out
    assert "[SDD] Total" in out


def test_prints_slow_warning_for_watchdog_marked_phase(capsys) -> None:
    timer = PhaseTimer(thresholds_ms={"ask.governance.snapshot": 0})
    with timer.phase("ask.governance.snapshot", latency_domain="governance"):
        time.sleep(0.01)
    entry_mono = time.monotonic() - 0.02

    print_ask_console_summary(timer, entry_mono=entry_mono)

    captured = capsys.readouterr()
    assert "is slow" in captured.err
    assert "elapsed=" in captured.err
    assert "threshold=" in captured.err


def test_no_slow_warning_when_no_threshold_exceeded(capsys) -> None:
    timer = PhaseTimer()
    with timer.phase("ask.governance.snapshot", latency_domain="governance"):
        time.sleep(0.01)
    entry_mono = time.monotonic() - 0.02

    print_ask_console_summary(timer, entry_mono=entry_mono)

    captured = capsys.readouterr()
    assert "is slow" not in captured.err
