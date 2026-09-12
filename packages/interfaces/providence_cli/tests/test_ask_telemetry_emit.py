"""Tests for _emit_ask_telemetry  duration/timestamps, OtelBridge, TelemetrySink."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_emit_kwargs(**overrides):
    base = dict(
        command="ask",
        workspace_root=Path("/tmp/fake-ws"),
        trace_id="trace-abc",
        agent_id="test-agent",
        fingerprint="abc123",
        context_source="compiled",
        mandates_count=5,
        profile="client",
        state="HEALTHY",
        drift_detected=False,
    )
    base.update(overrides)
    return base


def _event_path_id(event: object) -> str | None:
    """Read path_id from either event object or dict payload."""
    if isinstance(event, dict):
        return event.get("path_id")
    return getattr(event, "path_id", None)


def test_duration_and_timestamps_passed_to_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from providence_cli.commands._ask_backend import _emit_ask_telemetry

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    (tmp_path / ".providence" / "runtime").mkdir(parents=True)
    (tmp_path / ".providence" / "profile").write_text(
        "[sdd]\nworkspace_id=test-ws\n", encoding="utf-8"
    )

    captured: list = []

    class _FakeSink:
        def __init__(self, **_):
            pass

        def emit(self, event):
            captured.append(event)

    with patch("providence_cli.commands._ask_backend.TelemetrySink", _FakeSink):
        _emit_ask_telemetry(
            "governance.ask",
            **_make_emit_kwargs(workspace_root=tmp_path),
            start_ts="2026-05-20T00:00:00Z",
            end_ts="2026-05-20T00:00:01Z",
            duration_ms=42,
            path_id="PATH_A",
        )

    assert len(captured) == 1
    ev = captured[0]
    assert ev.duration_ms == 42
    assert ev.start_ts == "2026-05-20T00:00:00Z"
    assert ev.end_ts == "2026-05-20T00:00:01Z"
    assert _event_path_id(ev) == "PATH_A"


def test_phase_slow_flag_passed_through_to_runtime_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from providence_cli.commands._ask_backend import _emit_ask_telemetry

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    (tmp_path / ".providence" / "runtime").mkdir(parents=True)
    (tmp_path / ".providence" / "profile").write_text(
        "[sdd]\nworkspace_id=test-ws\n", encoding="utf-8"
    )

    captured: list = []

    class _FakeSink:
        def __init__(self, **_):
            pass

        def emit(self, event):
            captured.append(event)

    with patch("providence_cli.commands._ask_backend.TelemetrySink", _FakeSink):
        _emit_ask_telemetry(
            "governance.ask.phase",
            **_make_emit_kwargs(workspace_root=tmp_path),
            phase_slow=True,
        )

    assert captured[0].phase_slow is True


def test_phase_slow_flag_defaults_to_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from providence_cli.commands._ask_backend import _emit_ask_telemetry

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    (tmp_path / ".providence" / "runtime").mkdir(parents=True)
    (tmp_path / ".providence" / "profile").write_text(
        "[sdd]\nworkspace_id=test-ws\n", encoding="utf-8"
    )

    captured: list = []

    class _FakeSink:
        def __init__(self, **_):
            pass

        def emit(self, event):
            captured.append(event)

    with patch("providence_cli.commands._ask_backend.TelemetrySink", _FakeSink):
        _emit_ask_telemetry(
            "governance.ask.phase",
            **_make_emit_kwargs(workspace_root=tmp_path),
        )

    assert captured[0].phase_slow is False


def test_otel_bridge_used_when_endpoint_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from providence_cli.commands._ask_backend import _emit_ask_telemetry

    monkeypatch.setenv("SDD_OTEL_ENDPOINT", "http://otel.example.com:4318")
    (tmp_path / ".providence").mkdir()
    (tmp_path / ".providence" / "profile").write_text(
        "[sdd]\nworkspace_id=test-ws\n", encoding="utf-8"
    )

    mock_bridge_instance = MagicMock()
    mock_bridge_cls = MagicMock(return_value=mock_bridge_instance)
    mock_exporter = MagicMock()
    mock_exporter_cls = MagicMock(return_value=mock_exporter)

    with (
        patch(
            "providence_cli.commands._ask_backend.OtelBridge",
            mock_bridge_cls,
            create=True,
        ),
        patch(
            "providence_cli.commands._ask_backend.OtlpHttpExporter",
            mock_exporter_cls,
            create=True,
        ),
        patch("providence_runtime.OtelBridge", mock_bridge_cls),
        patch("providence_runtime.otel.OtlpHttpExporter", mock_exporter_cls),
    ):
        _emit_ask_telemetry(
            "governance.ask",
            **_make_emit_kwargs(workspace_root=tmp_path),
        )

    mock_bridge_instance.emit.assert_called_once()


def test_telemetry_sink_used_without_otel_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from providence_cli.commands._ask_backend import _emit_ask_telemetry

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    (tmp_path / ".providence").mkdir()
    (tmp_path / ".providence" / "profile").write_text(
        "[sdd]\nworkspace_id=test-ws\n", encoding="utf-8"
    )

    captured: list = []

    class _FakeSink:
        def __init__(self, **_):
            pass

        def emit(self, event):
            captured.append(event)

    with patch("providence_cli.commands._ask_backend.TelemetrySink", _FakeSink):
        _emit_ask_telemetry(
            "governance.ask",
            **_make_emit_kwargs(workspace_root=tmp_path),
        )

    assert len(captured) == 1
