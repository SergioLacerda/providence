from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from providence_cli.services import runtime_handler as runtime_mod
from providence_cli.services import runtime_handler_status as runtime_status_mod


def test_read_workspace_id_and_profile_from_ini(tmp_path: Path, monkeypatch) -> None:
    profile = tmp_path / ".providence" / "profile"
    profile.parent.mkdir(parents=True)
    profile.write_text("[sdd]\nworkspace_id = ws-1\ntype = client\n", encoding="utf-8")
    monkeypatch.setattr(runtime_mod, "profile_active_path", lambda root: profile)
    assert runtime_mod._read_workspace_id(tmp_path) == "ws-1"
    assert runtime_mod._read_profile(tmp_path) == "client"


def test_check_cache_staleness_and_footer_status(tmp_path: Path) -> None:
    assert runtime_status_mod._check_cache_staleness(tmp_path)["missing"] is True
    cache = tmp_path / ".providence" / "runtime" / ".providence-cache.md"
    cache.parent.mkdir(parents=True)
    cache.write_text("x", encoding="utf-8")
    info = runtime_status_mod._check_cache_staleness(tmp_path)
    assert info["missing"] is False
    assert (
        runtime_status_mod._footer_drift_status(
            {"detected": True, "type": "spec_drift"}
        )
        == "spec_drift"
    )
    assert (
        runtime_status_mod._footer_drift_status(
            {"detected": False, "type": "spec_drift"}
        )
        == "none"
    )


def test_normalize_report_and_show_ask_confidence(tmp_path: Path, capsys) -> None:
    report = SimpleNamespace(ok=True, other=Path("/tmp/x"))
    normalized = runtime_mod._normalize_report(report)
    assert normalized["ok"] is True
    assert normalized["other"] == "/tmp/x"

    state = tmp_path / ".providence" / "runtime" / "governance-state.json"
    state.parent.mkdir(parents=True)
    state.write_text(
        json.dumps(
            {
                "last_ask": {
                    "ts": "now",
                    "context_source": "compiled",
                    "compiled_fingerprint_used": "fp",
                    "trace_id": "1234567890",
                }
            }
        ),
        encoding="utf-8",
    )
    payload = runtime_mod._show_ask_confidence(tmp_path)
    captured = capsys.readouterr()
    assert payload is not None
    assert payload["trace_id"] == "12345678"
    assert "ask_confidence" in captured.out


def test_emit_runtime_status_handles_missing_compiled_dir(
    monkeypatch, tmp_path: Path
) -> None:
    fake = ModuleType("providence_runtime")
    fake.CompiledArtifact = SimpleNamespace(
        from_sdd_compiled_dir=lambda compiled_dir, profile: None
    )
    fake.DriftDetector = lambda: SimpleNamespace(classify=lambda **kwargs: None)
    fake.GovernanceInjector = lambda: SimpleNamespace(
        inject_from_path=lambda path: SimpleNamespace(
            loaded=False,
            artifact_fingerprint="fp",
            schema_version="1",
            mandates_loaded=0,
        )
    )
    fake.RuntimeEvent = lambda **kwargs: kwargs
    fake.SessionManager = lambda state_dir: SimpleNamespace(
        upsert=lambda session: None,
        get=lambda workspace_id, agent_id, work_item_id: None,
    )
    fake.SessionState = lambda **kwargs: kwargs
    fake.TelemetrySink = lambda jsonl_path, logging_mode: SimpleNamespace(
        emit=lambda event: None
    )
    monkeypatch.setitem(sys.modules, "providence_runtime", fake)
    monkeypatch.setattr(
        runtime_mod, "compiled_active_dir", lambda root: tmp_path / "missing"
    )
    assert (
        runtime_mod._emit_runtime_status(
            root=tmp_path,
            ahp_state="HEALTHY",
            workspace_profile="client",
            current_profile="client",
        )["type"]
        == "none"
    )


def test_emit_runtime_status_emits_drift(monkeypatch, tmp_path: Path) -> None:
    compiled = tmp_path / ".providence" / "compiled"
    compiled.mkdir(parents=True)
    events: list[dict] = []
    emitted: list[str] = []

    class _FakeDriftReport:
        drift_detected = True
        drift_type = "spec_drift"
        remediation_command = "providence governance compile"

    fake = ModuleType("providence_runtime")
    fake.CompiledArtifact = SimpleNamespace(
        from_sdd_compiled_dir=lambda compiled_dir, profile: object()
    )
    fake.DriftDetector = lambda: SimpleNamespace(
        classify=lambda **kwargs: _FakeDriftReport()
    )
    fake.GovernanceInjector = lambda: SimpleNamespace(
        inject_from_path=lambda path: SimpleNamespace(
            loaded=True,
            artifact_fingerprint="fp",
            schema_version="1",
            mandates_loaded=16,
        )
    )
    fake.RuntimeEvent = lambda **kwargs: kwargs
    fake.SessionManager = lambda state_dir: SimpleNamespace(
        upsert=lambda session: None,
        get=lambda workspace_id, agent_id, work_item_id: SimpleNamespace(
            artifact_fingerprint="old-fp"
        ),
    )
    fake.SessionState = lambda **kwargs: kwargs
    fake.TelemetrySink = lambda jsonl_path, logging_mode: SimpleNamespace(
        emit=lambda event: events.append(event)
    )
    monkeypatch.setitem(sys.modules, "providence_runtime", fake)
    monkeypatch.setattr(runtime_mod, "compiled_active_dir", lambda root: compiled)
    monkeypatch.setattr(
        runtime_mod,
        "resolve_compliance_events_path",
        lambda workspace_root: workspace_root / "events.jsonl",
    )
    info = runtime_mod._emit_runtime_status(
        root=tmp_path,
        ahp_state="HEALTHY",
        workspace_profile="client",
        current_profile="client",
        emit_fn=lambda msg: emitted.append(msg),
    )
    assert info["detected"] is True
    assert events[0]["event"] == "runtime.session.start"
    assert events[1]["event"] == "runtime.drift.detected"
    assert "spec_drift" in emitted[0]


def test_emit_runtime_status_classifies_against_previous_session_not_current(
    monkeypatch, tmp_path: Path
) -> None:
    """DRF-03 regression: `classify()` must receive the session persisted on
    a *prior* call, never the session object just built from the current
    artifact  comparing the artifact to a session built from itself always
    reports "aligned" regardless of real drift.
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` DRF-03.
    """
    compiled = tmp_path / ".providence" / "compiled"
    compiled.mkdir(parents=True)

    class _RealishSessionManager:
        """Persists across calls within the test, like the real SessionManager."""

        def __init__(self, state_dir):
            self._sessions: dict[tuple, object] = {}

        def get(self, workspace_id, agent_id, work_item_id):
            return self._sessions.get((workspace_id, agent_id, work_item_id))

        def upsert(self, session):
            key = (
                session["workspace_id"],
                session["agent_id"],
                session["work_item_id"],
            )
            self._sessions[key] = session

    manager_holder: dict[str, _RealishSessionManager] = {}

    def _make_manager(state_dir):
        if "instance" not in manager_holder:
            manager_holder["instance"] = _RealishSessionManager(state_dir)
        return manager_holder["instance"]

    classify_calls: list[dict] = []

    def _classify(**kwargs):
        classify_calls.append(kwargs)
        session = kwargs["session"]
        artifact = kwargs["artifact"]
        session_fp = (
            session["artifact_fingerprint"]
            if isinstance(session, dict)
            else session.artifact_fingerprint
        )
        return SimpleNamespace(
            drift_detected=session_fp != artifact.fingerprint,
            drift_type="fingerprint_mismatch"
            if session_fp != artifact.fingerprint
            else "none",
            remediation_command="providence governance compile",
        )

    current_fp = {"value": "fp-v1"}
    fake = ModuleType("providence_runtime")
    fake.CompiledArtifact = SimpleNamespace(
        from_sdd_compiled_dir=lambda compiled_dir, profile: SimpleNamespace(
            fingerprint=current_fp["value"], profile=profile
        )
    )
    fake.DriftDetector = lambda: SimpleNamespace(classify=_classify)
    fake.GovernanceInjector = lambda: SimpleNamespace(
        inject_from_path=lambda path: SimpleNamespace(
            loaded=True,
            artifact_fingerprint=current_fp["value"],
            schema_version="1",
            mandates_loaded=1,
        )
    )
    fake.RuntimeEvent = lambda **kwargs: kwargs
    fake.SessionManager = _make_manager
    fake.SessionState = lambda **kwargs: kwargs
    fake.TelemetrySink = lambda jsonl_path, logging_mode: SimpleNamespace(
        emit=lambda event: None
    )
    monkeypatch.setitem(sys.modules, "providence_runtime", fake)
    monkeypatch.setattr(runtime_mod, "compiled_active_dir", lambda root: compiled)
    monkeypatch.setattr(
        runtime_mod,
        "resolve_compliance_events_path",
        lambda workspace_root: workspace_root / "events.jsonl",
    )

    # First call: no previous session exists yet  must not report drift.
    first = runtime_mod._emit_runtime_status(
        root=tmp_path,
        ahp_state="HEALTHY",
        workspace_profile="client",
        current_profile="client",
    )
    assert first["detected"] is False
    assert classify_calls == []  # no baseline to classify against yet

    # Second call, same fingerprint: previous session now exists and matches.
    second = runtime_mod._emit_runtime_status(
        root=tmp_path,
        ahp_state="HEALTHY",
        workspace_profile="client",
        current_profile="client",
    )
    assert second["detected"] is False
    assert classify_calls[-1]["session"]["artifact_fingerprint"] == "fp-v1"

    # Third call, artifact fingerprint changed: must now detect drift by
    # comparing against the *previous* session (fp-v1), not the new one.
    current_fp["value"] = "fp-v2"
    third = runtime_mod._emit_runtime_status(
        root=tmp_path,
        ahp_state="HEALTHY",
        workspace_profile="client",
        current_profile="client",
    )
    assert third["detected"] is True
    assert classify_calls[-1]["session"]["artifact_fingerprint"] == "fp-v1"
    assert classify_calls[-1]["artifact"].fingerprint == "fp-v2"
