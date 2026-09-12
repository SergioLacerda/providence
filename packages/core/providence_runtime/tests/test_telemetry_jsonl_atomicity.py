"""Atomicity/durability guards for TelemetrySink JSONL append (A6).

Regression coverage for the risk noted in the initial critique: concurrent
writers appending to the same compliance-events.jsonl segment could
interleave partial lines, and a crash right after emit() could lose an event
that only ever reached the OS page cache. `_write_jsonl` now takes an
exclusive advisory lock around the write and fsyncs before returning.
"""

from __future__ import annotations

import json
import multiprocessing
from pathlib import Path

import pytest
from providence_runtime import RuntimeEvent, TelemetrySink
from providence_runtime.telemetry import MODE_ACTIVE


def _make_event(event_name: str) -> RuntimeEvent:
    return RuntimeEvent(event=event_name, command="runtime", status="ok", trace_id="t1")


def _write_events_in_subprocess(jsonl_path_str: str, count: int, tag: str) -> None:
    """Target for a real OS subprocess — writes `count` events, one at a time.

    Module-level (not a closure) so it is importable/picklable by
    `multiprocessing`'s spawn start method as well as fork.
    """
    path = Path(jsonl_path_str)
    for i in range(count):
        sink = TelemetrySink(jsonl_path=path, logging_mode=MODE_ACTIVE)
        sink.emit(
            RuntimeEvent(
                event="runtime.session.start",
                command="runtime",
                status="ok",
                trace_id=f"{tag}-{i}",
            )
        )


def test_write_jsonl_locks_and_fsyncs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Every append takes an exclusive flock and calls os.fsync before releasing it."""
    calls: list[str] = []

    import providence_runtime.telemetry._sink as sink_module

    class _FakeFcntl:
        LOCK_EX = 2
        LOCK_UN = 8

        @staticmethod
        def flock(fd: int, op: int) -> None:
            calls.append(f"flock:{op}")

    real_fsync = sink_module.os.fsync

    def _tracking_fsync(fd: int) -> None:
        calls.append("fsync")
        real_fsync(fd)

    monkeypatch.setattr(sink_module, "fcntl", _FakeFcntl)
    monkeypatch.setattr(sink_module.os, "fsync", _tracking_fsync)

    jsonl_path = tmp_path / "compliance-events.jsonl"
    sink = TelemetrySink(jsonl_path=jsonl_path, logging_mode=MODE_ACTIVE)
    sink.emit(_make_event("runtime.session.start"))

    assert calls == [f"flock:{_FakeFcntl.LOCK_EX}", "fsync"]
    assert jsonl_path.read_text(encoding="utf-8").strip()


def test_write_jsonl_releases_lock_even_when_fsync_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A failed fsync must not leave the file handle (and its flock) dangling."""
    import providence_runtime.telemetry._sink as sink_module

    calls: list[str] = []

    class _FakeFcntl:
        LOCK_EX = 2
        LOCK_UN = 8

        @staticmethod
        def flock(fd: int, op: int) -> None:
            calls.append(f"flock:{op}")

    def _raising_fsync(fd: int) -> None:
        raise OSError("simulated disk full")

    monkeypatch.setattr(sink_module, "fcntl", _FakeFcntl)
    monkeypatch.setattr(sink_module.os, "fsync", _raising_fsync)

    jsonl_path = tmp_path / "compliance-events.jsonl"
    sink = TelemetrySink(jsonl_path=jsonl_path, logging_mode=MODE_ACTIVE)

    with pytest.raises(OSError, match="simulated disk full"):
        sink.emit(_make_event("runtime.session.start"))

    # The file handle closes (context manager exit) even though fsync raised,
    # so a second writer can still acquire the lock afterwards.
    monkeypatch.setattr(sink_module.os, "fsync", lambda fd: None)
    sink.emit(_make_event("runtime.session.start"))
    assert jsonl_path.read_text(encoding="utf-8").strip()


def test_sensitive_event_missing_traceability_fields_logs_warning(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    """TEL-01 regression: `TraceabilityValidator` existed but `TelemetrySink`
    never invoked it, so a sensitive event missing its required fields
    (workspace_id, agent_id, decision_source_refs) was persisted silently,
    indistinguishable from a compliant one.
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` TEL-01.
    """
    jsonl_path = tmp_path / "compliance-events.jsonl"
    sink = TelemetrySink(jsonl_path=jsonl_path, logging_mode=MODE_ACTIVE)

    # "governance.violation" is a sensitive event per validator.py's
    # _SENSITIVE_EVENTS — missing workspace_id/agent_id/decision_source_refs.
    event = RuntimeEvent(
        event="governance.violation", command="runtime", status="error", trace_id="t1"
    )
    with caplog.at_level("WARNING", logger="providence_runtime.telemetry._sink"):
        sink.emit(event)

    assert any(
        "missing required traceability fields" in record.message
        for record in caplog.records
    )
    # Still persisted — the sink stays best-effort/non-blocking; the point is
    # visibility, not enforcement at this layer.
    assert jsonl_path.read_text(encoding="utf-8").strip()


def test_compliant_sensitive_event_does_not_warn(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    jsonl_path = tmp_path / "compliance-events.jsonl"
    sink = TelemetrySink(jsonl_path=jsonl_path, logging_mode=MODE_ACTIVE)

    event = RuntimeEvent(
        event="governance.violation",
        command="runtime",
        status="error",
        trace_id="t1",
        workspace_id="ws-1",
        agent_id="agent-1",
        decision_source_refs=["M001"],
    )
    with caplog.at_level("WARNING", logger="providence_runtime.telemetry._sink"):
        sink.emit(event)

    assert not any(
        "missing required traceability fields" in record.message
        for record in caplog.records
    )


def test_write_jsonl_survives_real_multiprocess_contention(tmp_path: Path) -> None:
    """TST-01 regression: prior coverage only checked that a *mocked* fcntl
    was called, never real contention between OS processes. This spawns
    actual subprocesses (`multiprocessing.Process`, no external provider)
    appending to the same segment concurrently and verifies every write
    survives intact — no lost lines, no interleaved/corrupted JSON.
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` TST-01.
    """
    jsonl_path = tmp_path / "compliance-events.jsonl"
    processes_count = 4
    events_per_process = 25

    if "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("requires multiprocessing 'fork' start method")

    ctx = multiprocessing.get_context("fork")
    procs = [
        ctx.Process(
            target=_write_events_in_subprocess,
            args=(str(jsonl_path), events_per_process, f"proc{i}"),
        )
        for i in range(processes_count)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)
        assert p.exitcode == 0

    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    # No lost or interleaved writes: exactly one valid JSON object per line.
    assert len(lines) == processes_count * events_per_process
    trace_ids = {json.loads(line)["trace_id"] for line in lines}
    assert len(trace_ids) == processes_count * events_per_process
