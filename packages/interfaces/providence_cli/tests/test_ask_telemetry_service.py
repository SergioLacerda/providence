"""Coverage tests for `providence_cli.services.ask_telemetry`."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from providence_cli.services import ask_telemetry as telemetry_mod


class _Logger:
    def __init__(self) -> None:
        self.debug_calls: list[tuple[object, ...]] = []

    def debug(self, *args: object) -> None:
        self.debug_calls.append(args)


def _install_fake_providence_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    root = types.ModuleType("providence_runtime")

    class _RuntimeEvent(dict):
        pass

    class _TelemetrySink:
        def __init__(self, jsonl_path: Path, logging_mode: str) -> None:
            self.jsonl_path = jsonl_path
            self.logging_mode = logging_mode
            self.events: list[object] = []

        def emit(self, event: object) -> None:
            self.events.append(event)

    class _OtelBridge:
        def __init__(self, exporter: object, jsonl_path: Path) -> None:
            self.exporter = exporter
            self.jsonl_path = jsonl_path
            self.events: list[object] = []

        def emit(self, event: object) -> None:
            self.events.append(event)

    class _SessionState(types.SimpleNamespace):
        pass

    class _SessionManager:
        def __init__(self, state_dir: Path) -> None:
            self.state_dir = state_dir
            self.sessions: list[object] = []

        def upsert(self, session: object) -> None:
            self.sessions.append(session)

    class _OtlpHttpExporter:
        def __init__(self, endpoint: str) -> None:
            self.endpoint = endpoint

    root.RuntimeEvent = _RuntimeEvent
    root.TelemetrySink = _TelemetrySink
    root.OtelBridge = _OtelBridge
    root.SessionState = _SessionState
    root.SessionManager = _SessionManager
    monkeypatch.setitem(sys.modules, "providence_runtime", root)

    otel_mod = types.ModuleType("providence_runtime.otel")
    otel_mod.OtlpHttpExporter = _OtlpHttpExporter
    monkeypatch.setitem(sys.modules, "providence_runtime.otel", otel_mod)


def test_resolve_tokens_env_estimated_and_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SDD_TOKENS_INPUT", raising=False)
    monkeypatch.delenv("SDD_TOKENS_OUTPUT", raising=False)
    assert telemetry_mod.resolve_tokens("abcd", "abcdefgh") == (1, 2, "estimated")

    monkeypatch.setenv("SDD_TOKENS_INPUT", "10")
    monkeypatch.setenv("SDD_TOKENS_OUTPUT", "20")
    assert telemetry_mod.resolve_tokens("abcd", "abcdefgh") == (10, 20, "env")

    monkeypatch.setattr(
        telemetry_mod.os.environ,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert telemetry_mod.resolve_tokens("abcd", "abcdefgh") == (None, None, "unknown")


def test_emit_ask_telemetry_uses_passive_sink_and_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_providence_runtime(monkeypatch)
    monkeypatch.setattr(
        telemetry_mod,
        "resolve_compliance_events_path",
        lambda workspace_root: tmp_path / "events.jsonl",
    )
    (tmp_path / ".providence").mkdir()
    (tmp_path / ".providence" / "profile").write_text(
        "[sdd]\nworkspace_id = ws-1\n", encoding="utf-8"
    )

    telemetry_mod.emit_ask_telemetry(
        "ask.finished",
        command="ask",
        workspace_root=tmp_path,
        trace_id="trace-1",
        agent_id="agent-1",
        fingerprint="fp-1",
        context_source="compiled",
        mandates_count=3,
        profile="client",
        state="HEALTHY",
        drift_detected=False,
        query_hash="qh",
        path_id="path-1",
        start_ts="2025-01-01T00:00:00Z",
        end_ts="2025-01-01T00:00:01Z",
        duration_ms=10,
        context_bytes_loaded=100,
        tokens_input=1,
        tokens_output=2,
        retry_count=0,
        compression_ratio=1.5,
        extra_details={"extra": True},
    )


def test_emit_ask_telemetry_uses_otel_bridge_and_handles_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_providence_runtime(monkeypatch)
    monkeypatch.setattr(
        telemetry_mod,
        "resolve_compliance_events_path",
        lambda workspace_root: tmp_path / "events.jsonl",
    )
    (tmp_path / ".providence").mkdir()
    (tmp_path / ".providence" / "profile").write_text("not valid ini", encoding="utf-8")
    monkeypatch.setenv("SDD_OTEL_ENDPOINT", "http://otel.local")
    logger = _Logger()

    telemetry_mod.emit_ask_telemetry(
        "ask.finished",
        command="ask",
        workspace_root=tmp_path,
        trace_id="trace-2",
        agent_id="agent-2",
        fingerprint="fp-2",
        context_source="runtime",
        mandates_count=1,
        profile="client",
        state="PARTIAL",
        drift_detected=True,
        logger=logger,
    )

    assert logger.debug_calls


def test_emit_ask_telemetry_handles_sink_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_providence_runtime(monkeypatch)
    monkeypatch.setattr(
        telemetry_mod,
        "resolve_compliance_events_path",
        lambda workspace_root: tmp_path / "events.jsonl",
    )

    class _BrokenSink:
        def __init__(self, jsonl_path: Path, logging_mode: str) -> None:
            raise RuntimeError("sink boom")

    logger = _Logger()
    telemetry_mod.emit_ask_telemetry(
        "ask.finished",
        command="ask",
        workspace_root=tmp_path,
        trace_id="trace-3",
        agent_id="agent-3",
        fingerprint="fp-3",
        context_source="compiled",
        mandates_count=1,
        profile="client",
        state="FAILED",
        drift_detected=False,
        logger=logger,
        telemetry_sink_cls=_BrokenSink,  # type: ignore[arg-type]
    )
    assert logger.debug_calls


def test_emit_ask_telemetry_records_durable_degradation_for_sensitive_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TEL-02 regression: a sensitive event's emission failure must leave a
    durable, inspectable record  not only an invisible `logger.debug` call
     per M007/M008's stronger obligations for sensitive decisions.
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` TEL-02.
    """
    _install_fake_providence_runtime(monkeypatch)
    monkeypatch.setattr(
        telemetry_mod,
        "resolve_compliance_events_path",
        lambda workspace_root: tmp_path / "events.jsonl",
    )

    class _BrokenSink:
        def __init__(self, jsonl_path: Path, logging_mode: str) -> None:
            raise RuntimeError("sink boom")

    logger = _Logger()
    result = telemetry_mod.emit_ask_telemetry(
        "governance.violation",  # sensitive per validator._SENSITIVE_EVENTS
        command="ask",
        workspace_root=tmp_path,
        trace_id="trace-4",
        agent_id="agent-4",
        fingerprint="fp-4",
        context_source="compiled",
        mandates_count=1,
        profile="client",
        state="FAILED",
        drift_detected=False,
        logger=logger,
        telemetry_sink_cls=_BrokenSink,  # type: ignore[arg-type]
    )

    # Still best-effort at the API boundary  never raises, returns None.
    assert result is None

    marker_path = tmp_path / ".providence" / "runtime" / "telemetry-degraded.jsonl"
    assert marker_path.exists()
    import json

    record = json.loads(marker_path.read_text(encoding="utf-8").strip())
    assert record["event"] == "governance.violation"
    assert "sink boom" in record["reason"]


def test_emit_ask_telemetry_non_sensitive_failure_does_not_write_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_providence_runtime(monkeypatch)
    monkeypatch.setattr(
        telemetry_mod,
        "resolve_compliance_events_path",
        lambda workspace_root: tmp_path / "events.jsonl",
    )

    class _BrokenSink:
        def __init__(self, jsonl_path: Path, logging_mode: str) -> None:
            raise RuntimeError("sink boom")

    telemetry_mod.emit_ask_telemetry(
        "ask.finished",  # not in _SENSITIVE_EVENTS
        command="ask",
        workspace_root=tmp_path,
        trace_id="trace-5",
        agent_id="agent-5",
        fingerprint="fp-5",
        context_source="compiled",
        mandates_count=1,
        profile="client",
        state="FAILED",
        drift_detected=False,
        telemetry_sink_cls=_BrokenSink,  # type: ignore[arg-type]
    )

    marker_path = tmp_path / ".providence" / "runtime" / "telemetry-degraded.jsonl"
    assert not marker_path.exists()


def test_upsert_ask_session_success_and_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_providence_runtime(monkeypatch)
    (tmp_path / ".providence").mkdir()
    (tmp_path / ".providence" / "profile").write_text(
        "[sdd]\nworkspace_id = ws-2\n", encoding="utf-8"
    )

    telemetry_mod.upsert_ask_session(tmp_path, "agent-4", "work-1", "fp-4")

    class _BrokenSessionManager:
        def __init__(self, state_dir: Path) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(telemetry_mod, "SessionManager", _BrokenSessionManager)
    logger = _Logger()
    telemetry_mod.upsert_ask_session(
        tmp_path, "agent-5", "work-2", "fp-5", logger=logger
    )
    assert logger.debug_calls
