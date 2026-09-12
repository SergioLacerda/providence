"""Tests for T-04: collapsing the end-of-call `governance-state.json`
read-modify-write cycles into one, and batching telemetry flushes.

`write_runtime_cache` + `store_routing_decision` always ran back-to-back at
the end of a `providence ask` call, each independently reading and writing
`governance-state.json`. `write_runtime_cache_and_routing_decision` combines
them into a single read + single write (design.md D4).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from providence_cli.services import ask_context_drift as ask_context_drift_mod
from providence_cli.services import ask_context_routing as ask_context_routing_mod


def test_write_runtime_cache_and_routing_decision_persists_both(
    tmp_path: Path,
) -> None:
    ask_context_routing_mod.write_runtime_cache_and_routing_decision(
        tmp_path,
        {"ts": "2026-01-01T00:00:00Z", "compiled_fingerprint_used": "fp1"},
        "query",
        "diagnose",
        "fp1",
        {
            "organize_used": True,
            "organize_reason": "heavy",
            "handbook_task_type": "diagnosis",
        },
    )

    state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))

    assert data["last_ask"]["compiled_fingerprint_used"] == "fp1"

    cached = ask_context_routing_mod.resolve_routing_decision(
        tmp_path, "query", "diagnose"
    )
    assert cached is not None
    assert cached["organize_used"] is True
    assert cached["handbook_task_type"] == "diagnosis"


def test_write_runtime_cache_and_routing_decision_reads_state_once(
    tmp_path: Path,
) -> None:
    """The combined write must do exactly one read of the state file, not the
    two independent reads `write_runtime_cache` + `store_routing_decision`
    would each perform on their own."""
    state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps({"spec_fingerprint": "existing"}), encoding="utf-8"
    )

    real_read_text = Path.read_text
    read_calls = {"count": 0}

    def _spy_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self == state_path:
            read_calls["count"] += 1
        return real_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", _spy_read_text):
        ask_context_routing_mod.write_runtime_cache_and_routing_decision(
            tmp_path,
            {"compiled_fingerprint_used": "fp1"},
            "query",
            None,
            "fp1",
            {"organize_used": False},
        )

    assert read_calls["count"] == 1


def test_write_runtime_cache_and_routing_decision_preserves_existing_data(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps({"spec_fingerprint": "existing123"}), encoding="utf-8"
    )

    ask_context_routing_mod.write_runtime_cache_and_routing_decision(
        tmp_path, {"ts": "now"}, "q", None, "", {"organize_used": False}
    )

    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["spec_fingerprint"] == "existing123"
    assert data["last_ask"]["ts"] == "now"


def test_write_runtime_cache_and_routing_decision_skips_routing_store_without_fingerprint(
    tmp_path: Path,
) -> None:
    """No fingerprint (e.g. degraded/unauthenticated call) -> last_ask is still
    written, but no routing-decision entry is cached against an empty key."""
    ask_context_routing_mod.write_runtime_cache_and_routing_decision(
        tmp_path, {"ts": "now"}, "q", None, "", {"organize_used": False}
    )

    state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert "last_routing_decisions" not in data


def test_write_runtime_cache_and_routing_decision_silently_handles_write_error(
    tmp_path: Path,
) -> None:
    with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
        ask_context_routing_mod.write_runtime_cache_and_routing_decision(
            tmp_path, {"ts": "now"}, "q", None, "fp1", {"organize_used": False}
        )


def test_check_fingerprint_drift_and_end_of_call_write_share_one_read(
    tmp_path: Path,
) -> None:
    """T-04a: `check_fingerprint_drift` (start of call) and
    `write_runtime_cache_and_routing_decision` (end of call) must share the
    per-process `_load_governance_state` cache instead of each independently
    reading `governance-state.json`  collapsing 2 reads + 1 write per `providence
    ask` call into 1 read + 1 write (design.md D-01)."""
    state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps({"last_ask": {"compiled_fingerprint_used": "fp1"}}),
        encoding="utf-8",
    )

    real_read_text = Path.read_text
    read_calls = {"count": 0}

    def _spy_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self == state_path:
            read_calls["count"] += 1
        return real_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", _spy_read_text):
        ask_context_drift_mod.check_fingerprint_drift(tmp_path, "fp1")
        ask_context_routing_mod.write_runtime_cache_and_routing_decision(
            tmp_path,
            {"compiled_fingerprint_used": "fp1"},
            "query",
            None,
            "fp1",
            {"organize_used": False},
        )

    assert read_calls["count"] == 1


def test_emit_ask_telemetry_reuses_shared_sink_and_skips_flush() -> None:
    """`sink=`/`flush=False` must reuse the caller's sink and not enqueue a
    flush  the caller batches all events onto one sink and flushes once."""
    from providence_cli.services.ask_telemetry import emit_ask_telemetry

    fake_sink = MagicMock()

    with patch("providence_cli.services.ask_telemetry.enqueue_flush") as fake_enqueue:
        event = emit_ask_telemetry(
            "governance.ask",
            command="ask",
            workspace_root=Path("/tmp/does-not-matter"),
            trace_id="trace-1",
            agent_id="agent-1",
            fingerprint="fp1",
            context_source="compiled",
            mandates_count=5,
            profile="client",
            state="HEALTHY",
            drift_detected=False,
            sink=fake_sink,
            flush=False,
        )

    assert event is not None
    fake_sink.emit.assert_called_once()
    fake_enqueue.assert_not_called()


def test_emit_ask_telemetry_flushes_when_no_sink_provided() -> None:
    """Default behavior (no shared sink) is unchanged: build one and flush."""
    from providence_cli.services.ask_telemetry import emit_ask_telemetry

    with (
        patch("providence_cli.services.ask_telemetry.build_sink") as fake_build_sink,
        patch("providence_cli.services.ask_telemetry.enqueue_flush") as fake_enqueue,
    ):
        fake_sink = MagicMock()
        fake_build_sink.return_value = fake_sink

        emit_ask_telemetry(
            "governance.ask",
            command="ask",
            workspace_root=Path("/tmp/does-not-matter"),
            trace_id="trace-1",
            agent_id="agent-1",
            fingerprint="fp1",
            context_source="compiled",
            mandates_count=5,
            profile="client",
            state="HEALTHY",
            drift_detected=False,
        )

    fake_sink.emit.assert_called_once()
    fake_enqueue.assert_called_once_with(fake_sink)
