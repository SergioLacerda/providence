"""Tests for default ask phase watchdog thresholds and the ask.cli.entry phase."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from providence_cli.commands._ask_backend._phase_timeouts import (
    DEFAULT_ASK_PHASE_TIMEOUTS_MS,
    DEFAULT_ASK_TIMEOUT_MS,
)


def test_default_ask_phase_timeouts_cover_all_known_phases():
    """Every phase this mission introduced or measures must have an explicit
    threshold so the watchdog never silently ignores a phase."""
    expected_phases = {
        "ask.cli.entry",
        "ask.budget.guard",
        "ask.workspace.resolve",
        "ask.organize.intake",
        "ask.handshake.guard",
        "ask.profile.resolve",
        "ask.runtime.handbook",
        "ask.governance.snapshot",
        "ask.response.render",
        "ask.telemetry.emit",
        "ask.external.llm_exchange",
    }
    assert expected_phases.issubset(DEFAULT_ASK_PHASE_TIMEOUTS_MS.keys())
    assert all(v > 0 for v in DEFAULT_ASK_PHASE_TIMEOUTS_MS.values())
    assert DEFAULT_ASK_TIMEOUT_MS > 0


def test_llm_exchange_threshold_is_much_higher_than_local_phases():
    """LLM latency is expected to legitimately take seconds  its threshold
    must not be tight like a local governance phase, or the watchdog would
    constantly false-positive on normal LLM latency."""
    llm_threshold = DEFAULT_ASK_PHASE_TIMEOUTS_MS["ask.external.llm_exchange"]
    local_threshold = DEFAULT_ASK_PHASE_TIMEOUTS_MS["ask.governance.snapshot"]
    assert llm_threshold > local_threshold * 10


def _start_session_with_backend_mocked(tmp_path: Path, *, entry_mono: float | None):
    from providence_cli.commands._ask_backend._pipeline_session import (
        _start_ask_session,
    )

    with (
        patch("providence_cli.commands._ask_backend._guard_budget_breach"),
        patch(
            "providence_cli.commands._ask_backend._resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "providence_cli.commands._ask_backend._run_organize_intake",
            return_value=(False, "light_input", None, 0, "indexed_only", None),
        ),
        patch("providence_cli.commands._ask_backend._guard_handshake"),
        patch(
            "providence_cli.commands._ask_backend._get_profile_state",
            return_value=("client", "HEALTHY"),
        ),
        patch("providence_cli.commands._ask_backend._emit_state_warnings"),
    ):
        if entry_mono is None:
            return _start_ask_session("test query", None)
        return _start_ask_session("test query", None, entry_mono=entry_mono)


def test_start_ask_session_without_entry_mono_records_no_cli_entry_phase(
    tmp_path: Path,
) -> None:
    session = _start_session_with_backend_mocked(tmp_path, entry_mono=None)
    phase_ids = [r.phase_id for r in session.phase_timer.records()]
    assert "ask.cli.entry" not in phase_ids


def test_start_ask_session_with_entry_mono_records_cli_entry_first(
    tmp_path: Path,
) -> None:
    entry_mono = time.monotonic()
    time.sleep(0.01)
    session = _start_session_with_backend_mocked(tmp_path, entry_mono=entry_mono)

    records = session.phase_timer.records()
    assert records[0].phase_id == "ask.cli.entry"
    assert records[0].duration_ms >= 10
    assert records[0].measurement_quality == "measured"
    assert records[0].observed_by == "providence_cli"


def test_start_ask_session_wires_default_watchdog_thresholds(tmp_path: Path) -> None:
    session = _start_session_with_backend_mocked(tmp_path, entry_mono=None)
    assert session.phase_timer.thresholds_ms == DEFAULT_ASK_PHASE_TIMEOUTS_MS
    assert session.phase_timer.default_threshold_ms == DEFAULT_ASK_TIMEOUT_MS
