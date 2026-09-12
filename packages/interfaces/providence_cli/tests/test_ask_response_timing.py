"""Tests for --full timing breakdown in providence ask text/JSON output."""

from __future__ import annotations

import json
from pathlib import Path

from providence_cli.commands._ask_backend._phase_timer import PhaseTimer
from providence_cli.services.ask_response import emit_ask_text_response
from providence_cli.services.ask_response_json import emit_ask_json_response
from providence_cli.services.ask_types import _AskInputs, _AskSessionContext

ASK_SNAPSHOT = {
    "context_source": "compiled",
    "fingerprint": "fp-1",
    "mandates_count": 3,
    "degraded": False,
    "degrade_reason": "",
    "trust_source": "verified",
    "drift_detected": False,
    "root_seed_drift_detected": False,
    "learning_signals": None,
    "handbook_lookup": None,
}


def _inputs(*, full: bool) -> _AskInputs:
    return _AskInputs(
        query="hello",
        dossier=False,
        skill=None,
        budget=None,
        full=full,
        log_path=None,
        log_format="jsonl",
        tokens_input=None,
        tokens_output=None,
    )


def _session(*, phase_timer: PhaseTimer) -> _AskSessionContext:
    return _AskSessionContext(
        workspace_root=Path("/tmp/workspace"),
        organize_used=False,
        organize_reason="light_input",
        organize_artifact_path="",
        organize_chunks=0,
        organize_retrieval="indexed_only",
        cached_handbook_task_type=None,
        profile="master",
        state="GREEN",
        agent_id="agent-1",
        trace_id="trace-1",
        start_mono=0.0,
        start_ts="2026-07-09T00:00:00Z",
        phase_timer=phase_timer,
    )


def _timer_with_records() -> PhaseTimer:
    timer = PhaseTimer()
    with timer.phase("ask.workspace.resolve", latency_domain="local_fs"):
        pass
    with timer.phase("ask.governance.snapshot", latency_domain="governance"):
        pass
    return timer


def _noop_dossier(*args: object, **kwargs: object) -> None:
    return None


def test_json_full_mode_includes_timing_block(capsys) -> None:
    timer = _timer_with_records()
    records = timer.records()
    inputs = _inputs(full=True)
    session = _session(phase_timer=timer)

    emit_ask_json_response(
        inputs,
        session,
        ASK_SNAPSHOT,
        "PROVIDENCE GOVERNANCE: drift=none",
        duration_ms=184,
        resolve_dossier_budget_fn=lambda budget: 100,
        load_dossier_artifact_fn=lambda root: None,
        build_dossier_lines_fn=lambda **kwargs: [],
        handle_dossier_error_fn=lambda exc: None,
        prefer_full_summary_fn=lambda: False,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    timing = payload["data"]["timing"]
    assert timing["total_ms"] == 184
    assert timing["phase_total_ms"] == timer.phase_total_ms()
    assert timing["unattributed_ms"] == timer.unattributed_ms(session_duration_ms=184)
    assert timing["phases"] == [
        {
            "phase_id": record.phase_id,
            "duration_ms": record.duration_ms,
            "latency_domain": record.latency_domain,
            "measurement_quality": record.measurement_quality,
            "phase_slow": record.phase_slow,
        }
        for record in records
    ]


def test_json_normal_mode_omits_timing_block(capsys) -> None:
    timer = _timer_with_records()
    inputs = _inputs(full=False)
    session = _session(phase_timer=timer)

    emit_ask_json_response(
        inputs,
        session,
        ASK_SNAPSHOT,
        "PROVIDENCE GOVERNANCE: drift=none",
        duration_ms=184,
        resolve_dossier_budget_fn=lambda budget: 100,
        load_dossier_artifact_fn=lambda root: None,
        build_dossier_lines_fn=lambda **kwargs: [],
        handle_dossier_error_fn=lambda exc: None,
        prefer_full_summary_fn=lambda: False,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert "timing" not in payload["data"]


def test_text_full_mode_prints_timing_block(capsys) -> None:
    timer = _timer_with_records()
    inputs = _inputs(full=True)
    session = _session(phase_timer=timer)

    emit_ask_text_response(
        inputs,
        session,
        ASK_SNAPSHOT,
        "output text",
        "PROVIDENCE GOVERNANCE: drift=none",
        duration_ms=184,
        build_and_output_dossier_fn=_noop_dossier,
    )

    captured = capsys.readouterr()
    assert "timing:" in captured.out
    assert "ask.workspace.resolve=" in captured.out
    assert "local_fs measured" in captured.out


def test_text_normal_mode_omits_timing_block(capsys) -> None:
    timer = _timer_with_records()
    inputs = _inputs(full=False)
    session = _session(phase_timer=timer)

    emit_ask_text_response(
        inputs,
        session,
        ASK_SNAPSHOT,
        "output text",
        "PROVIDENCE GOVERNANCE: drift=none",
        duration_ms=184,
        build_and_output_dossier_fn=_noop_dossier,
    )

    captured = capsys.readouterr()
    assert "timing:" not in captured.out
