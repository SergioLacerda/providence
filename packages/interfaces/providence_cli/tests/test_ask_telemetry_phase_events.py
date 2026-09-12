"""Tests for governance.ask.phase child event emission and trace linkage.

Pattern mirrors `test_ask_telemetry_emit.py` (FakeSink capturing real
`RuntimeEvent` objects via a patched `TelemetrySink`) combined with
`test_ask_telemetry_path_id.py` / `test_ask_telemetry_integration.py`
(driving the real `ask_cmd` entrypoint with the surrounding
guard/organize/snapshot/profile helpers mocked out).

Unlike the path_id/integration tests (which mock `_emit_ask_telemetry`
itself and only inspect the kwargs passed to it), these tests leave the
real `_emit_ask_telemetry` -> `emit_ask_telemetry` -> `TelemetrySink.emit`
chain intact so that real `RuntimeEvent` objects (with auto-generated
`span_id`/`parent_event_id`) are produced and can be inspected.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from providence_runtime import RuntimeEvent


def _run_ask_capture_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    query: str = "hello",
    drift_detected: bool = False,
) -> list[RuntimeEvent]:
    """Invoke ask_cmd with surrounding helpers mocked; return real RuntimeEvents."""
    from providence_cli.commands._ask_backend import ask_cmd

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")

    (tmp_path / ".providence" / "runtime").mkdir(parents=True)
    (tmp_path / ".providence" / "profile").write_text(
        "[sdd]\nworkspace_id=test-ws\n", encoding="utf-8"
    )

    captured: list[RuntimeEvent] = []

    class _FakeSink:
        def __init__(self, **_):
            pass

        def emit(self, event: RuntimeEvent) -> None:
            captured.append(event)

    fake_profile = MagicMock()
    fake_profile.as_dict.return_value = {
        "profile": "client",
        "name": "test",
        "workspace_id": "test-ws",
        "core_hash": "abc",
        "root": tmp_path,
        "is_master": False,
        "is_client": True,
    }

    with (
        patch("providence_cli.commands._ask_backend.TelemetrySink", _FakeSink),
        patch(
            "providence_core.utils.environment.resolve_profile",
            return_value=fake_profile,
        ),
        patch(
            "providence_cli.commands._ask_backend._resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "providence_cli.commands._ask_backend._get_profile_state",
            return_value=("client", "HEALTHY"),
        ),
        patch("providence_cli.commands._ask_backend._guard_budget_breach"),
        patch("providence_cli.commands._ask_backend._guard_handshake"),
        patch("providence_cli.commands._ask_backend._write_runtime_cache"),
        patch("providence_cli.commands._ask_backend._store_routing_decision"),
        patch("providence_cli.commands._ask_backend._upsert_ask_session"),
        patch("providence_cli.commands._ask_backend._emit_state_warnings"),
        patch(
            "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
            return_value={
                "query_hash": "bed9bd3e",
                "context_source": "compiled",
                "fingerprint": "abc",
                "mandates_count": 5,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "canonical",
                "drift_detected": drift_detected,
                "root_seed_drift_detected": False,
                "learning_signals": {},
                "learning_recommendation": None,
                "learning_context": {},
                "ask_decision_envelope": {},
            },
        ),
        patch(
            "providence_cli.commands._ask_backend._run_organize_intake",
            return_value=(False, "light_input", None, 0, "indexed_only", None),
        ),
        patch(
            "providence_cli.commands._ask_backend._governance_footer_for_state",
            return_value="",
        ),
    ):
        ask_cmd(query=query)

    return captured


def test_phase_events_share_parent_trace_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _run_ask_capture_events(tmp_path, monkeypatch)

    parent = next(e for e in captured if e.event == "governance.ask")
    phases = [e for e in captured if e.event == "governance.ask.phase"]

    assert len(phases) > 0
    for phase in phases:
        assert phase.trace_id == parent.trace_id
        assert phase.parent_event_id == parent.span_id
        assert phase.span_id != parent.span_id


def test_phase_events_have_required_detail_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _run_ask_capture_events(tmp_path, monkeypatch)
    phases = [e for e in captured if e.event == "governance.ask.phase"]

    assert len(phases) > 0
    for phase in phases:
        assert "phase_id" in phase.details
        assert "latency_domain" in phase.details
        assert "measurement_quality" in phase.details
        assert "observed_by" in phase.details


def test_phase_events_cover_expected_phase_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _run_ask_capture_events(tmp_path, monkeypatch)
    phases = [e for e in captured if e.event == "governance.ask.phase"]

    phase_ids = {phase.details.get("phase_id") for phase in phases}
    assert phase_ids == {
        "ask.cli.entry",
        "ask.budget.guard",
        "ask.workspace.resolve",
        "ask.organize.intake",
        "ask.handshake.guard",
        "ask.profile.resolve",
        "ask.governance.snapshot",
    }
    # ask.runtime.handbook is absent here because this test mocks
    # build_governed_ask_snapshot entirely (see module docstring)  the real
    # function is what records that phase. ask.response.render and
    # ask.telemetry.emit are absent for a structural reason: telemetry
    # emission (which produces these captured events) necessarily runs
    # before rendering, and cannot emit an event for its own still-running
    # phase  see _pipeline_runtime.py's _sync_ask_runtime/_ask_cmd_impl.


def test_llm_exchange_phase_absent_when_not_observable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SDD_ADAPTER_LLM_EXCHANGE_MS", raising=False)
    captured = _run_ask_capture_events(tmp_path, monkeypatch)
    phases = [e for e in captured if e.event == "governance.ask.phase"]
    llm_phases = [
        p for p in phases if p.details.get("phase_id") == "ask.external.llm_exchange"
    ]
    assert llm_phases == []


def test_llm_exchange_phase_present_when_adapter_reports_timing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SDD_ADAPTER_LLM_EXCHANGE_MS", "42")
    captured = _run_ask_capture_events(tmp_path, monkeypatch)
    phases = [e for e in captured if e.event == "governance.ask.phase"]
    llm_phases = [
        p for p in phases if p.details.get("phase_id") == "ask.external.llm_exchange"
    ]
    assert len(llm_phases) == 1
    llm_phase = llm_phases[0]
    assert llm_phase.duration_ms == 42
    assert llm_phase.details["measurement_quality"] == "adapter_reported"


def test_phase_events_carry_parent_drift_type_when_drift_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase sub-events must carry the parent's drift classification.

    Regression for `missing_drift_type` dominance in `providence audit summary`:
    phase events inherit `drift_detected=True` from the parent invocation but
    previously omitted `drift_type`, so one real drift rendered as ~6
    unclassified drift rows.
    """
    captured = _run_ask_capture_events(tmp_path, monkeypatch, drift_detected=True)
    parent = next(e for e in captured if e.event == "governance.ask")
    phases = [e for e in captured if e.event == "governance.ask.phase"]

    assert parent.details.get("drift_type") == "fingerprint_drift"
    assert len(phases) > 0
    for phase in phases:
        assert phase.details.get("drift_type") == "fingerprint_drift"


def test_phase_events_carry_drift_type_none_without_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _run_ask_capture_events(tmp_path, monkeypatch)
    phases = [e for e in captured if e.event == "governance.ask.phase"]

    assert len(phases) > 0
    for phase in phases:
        assert phase.details.get("drift_type") == "none"


def test_parent_governance_ask_still_emits_current_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: parent event fields unaffected by phase instrumentation."""
    captured = _run_ask_capture_events(tmp_path, monkeypatch)
    parent = next(e for e in captured if e.event == "governance.ask")

    assert parent.duration_ms is not None
    assert parent.trace_id
    assert parent.command == "ask"
    assert parent.details.get("context_source") == "compiled"
    assert parent.details.get("mandates_loaded") == 5
    assert parent.details.get("ahp_state") == "HEALTHY"
    assert parent.details.get("profile") == "client"
