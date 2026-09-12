"""Tests for the ask-pipeline phase timer helper."""

from __future__ import annotations

import time

import pytest

from providence_cli.commands._ask_backend._phase_timer import PhaseRecord, PhaseTimer


def test_phase_timer_records_single_phase():
    timer = PhaseTimer()
    with timer.phase("ask.workspace.resolve", latency_domain="local_fs"):
        time.sleep(0.01)

    records = timer.records()
    assert len(records) == 1
    record = records[0]
    assert isinstance(record, PhaseRecord)
    assert record.phase_id == "ask.workspace.resolve"
    assert record.latency_domain == "local_fs"
    assert record.duration_ms >= 10
    assert record.start_ts < record.end_ts
    assert record.measurement_quality == "measured"
    assert record.observed_by == "providence_cli"
    assert record.failed is False


def test_phase_timer_records_multiple_phases_in_order():
    timer = PhaseTimer()
    with timer.phase("ask.cli.entry", latency_domain="local_cli"):
        pass
    with timer.phase("ask.response.render", latency_domain="rendering"):
        pass

    ids = [r.phase_id for r in timer.records()]
    assert ids == ["ask.cli.entry", "ask.response.render"]


def _raise_boom() -> None:
    raise ValueError("boom")


def test_phase_timer_marks_failed_phase_and_reraises():
    timer = PhaseTimer()
    with pytest.raises(ValueError, match="boom"):  # noqa: SIM117 (nested to satisfy CodeQL unreachable-code check)
        with timer.phase("ask.governance.snapshot", latency_domain="governance"):
            _raise_boom()

    records = timer.records()
    assert len(records) == 1
    assert records[0].failed is True


def test_phase_timer_total_and_unattributed_ms():
    timer = PhaseTimer()
    with timer.phase("ask.cli.entry", latency_domain="local_cli"):
        time.sleep(0.01)

    total_ms = timer.phase_total_ms()
    assert total_ms >= 10

    unattributed = timer.unattributed_ms(session_duration_ms=total_ms + 50)
    assert unattributed == 50


def test_phase_timer_without_thresholds_never_marks_slow():
    timer = PhaseTimer()
    with timer.phase("ask.governance.snapshot", latency_domain="governance"):
        time.sleep(0.01)

    assert timer.records()[0].phase_slow is False
    assert timer.slow_records() == []


def test_phase_timer_marks_phase_slow_when_threshold_exceeded():
    timer = PhaseTimer(thresholds_ms={"ask.governance.snapshot": 0})
    with timer.phase("ask.governance.snapshot", latency_domain="governance"):
        time.sleep(0.01)

    record = timer.records()[0]
    assert record.phase_slow is True
    assert timer.slow_records() == [record]


def test_phase_timer_respects_default_threshold_for_unlisted_phase():
    timer = PhaseTimer(default_threshold_ms=0)
    with timer.phase("ask.some.new.phase", latency_domain="governance"):
        time.sleep(0.01)

    assert timer.records()[0].phase_slow is True


def test_phase_timer_per_phase_threshold_overrides_default():
    timer = PhaseTimer(
        thresholds_ms={"ask.workspace.resolve": 10_000}, default_threshold_ms=0
    )
    with timer.phase("ask.workspace.resolve", latency_domain="local_fs"):
        time.sleep(0.01)

    assert timer.records()[0].phase_slow is False


def test_phase_timer_watchdog_never_raises_or_changes_duration():
    """A soft watchdog must never affect control flow  only mark the record."""
    timer = PhaseTimer(default_threshold_ms=0)
    with timer.phase("ask.workspace.resolve", latency_domain="local_fs"):
        time.sleep(0.01)  # duration_ms must be > 0 to exceed a 0ms threshold

    record = timer.records()[0]
    assert record.phase_slow is True
    assert record.failed is False


def test_record_external_also_respects_watchdog_threshold():
    timer = PhaseTimer(thresholds_ms={"ask.external.llm_exchange": 10})
    timer.record_external(
        "ask.external.llm_exchange",
        latency_domain="external_llm",
        duration_ms=50,
        measurement_quality="adapter_reported",
        observed_by="adapter",
    )

    assert timer.records()[0].phase_slow is True


def test_threshold_for_reflects_dict_then_default_then_none():
    timer = PhaseTimer(
        thresholds_ms={"ask.governance.snapshot": 2000}, default_threshold_ms=1000
    )
    assert timer.threshold_for("ask.governance.snapshot") == 2000
    assert timer.threshold_for("ask.unlisted.phase") == 1000

    timer_no_default = PhaseTimer(thresholds_ms={"ask.governance.snapshot": 2000})
    assert timer_no_default.threshold_for("ask.unlisted.phase") is None
