"""Tests for metrics reload worker lifecycle and serve restart cycles."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer

from providence_cli.commands.metrics import _CollectorRef, _start_reload_worker, serve

pytestmark = pytest.mark.integration


class TestCollectorRef:
    def test_swap_updates_collector(self) -> None:
        initial = MagicMock()
        replacement = MagicMock()
        ref = _CollectorRef(initial)
        ref.swap(replacement)
        assert ref._collector is replacement

    def test_snapshot_delegates_to_collector(self) -> None:
        fake_snap = MagicMock()
        collector = MagicMock()
        collector.snapshot.return_value = fake_snap
        ref = _CollectorRef(collector)
        result = ref.snapshot()
        assert result is fake_snap


class TestStartReloadWorker:
    def test_reload_worker_calls_swap_on_tick(self, tmp_path) -> None:
        from unittest.mock import patch

        events = tmp_path / "events.jsonl"
        events.write_text("{}\n", encoding="utf-8")

        collector_ref = _CollectorRef(MagicMock())
        stop_event = threading.Event()

        fake_collector = MagicMock()
        with (
            patch("providence_runtime.reader.TelemetryReader"),
            patch("providence_runtime.metrics.TokenEconomyCollector") as mock_coll_cls,
        ):
            mock_coll_cls.from_reader.return_value = fake_collector
            worker = _start_reload_worker(
                jsonl_path=events,
                refresh=0,
                collector_ref=collector_ref,
                stop_event=stop_event,
            )
            stop_event.set()
            worker.join(timeout=2)

        assert not worker.is_alive()


class TestServeReloadAndRestartCycles:
    def test_reload_worker_stops_deterministically(
        self, metrics_events_path: Path
    ) -> None:
        """Reload worker should stop after stop_event is set."""
        from providence_runtime.metrics import TokenEconomyCollector
        from providence_runtime.reader import TelemetryReader

        collector = TokenEconomyCollector.from_reader(
            TelemetryReader(metrics_events_path)
        )
        collector_ref = _CollectorRef(collector)
        stop_event = threading.Event()
        worker = _start_reload_worker(
            jsonl_path=metrics_events_path,
            refresh=1,
            collector_ref=collector_ref,
            stop_event=stop_event,
        )
        stop_event.set()
        worker.join(timeout=2)
        assert not worker.is_alive()

    def test_serve_closes_server_on_keyboard_interrupt(
        self, metrics_events_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Serve should close HTTP server and exit cleanly on Ctrl+C."""
        closed = {"value": False}

        class FakeHTTPServer:
            timeout = 1.0

            def __init__(self, *_args: object, **_kwargs: object) -> None:
                pass

            def handle_request(self) -> None:
                raise KeyboardInterrupt

            def server_close(self) -> None:
                closed["value"] = True

        monkeypatch.setattr(
            "providence_cli.commands.metrics.http.server.HTTPServer", FakeHTTPServer
        )
        with pytest.raises(typer.Exit):
            serve(port=9996, jsonl=metrics_events_path, refresh=1)
        assert closed["value"] is True

    def test_serve_restart_cycle_multiple_times(
        self, metrics_events_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Serve should support repeated start/stop cycles without leaking state."""
        close_count = {"value": 0}

        class FakeHTTPServer:
            timeout = 1.0

            def __init__(self, *_args: object, **_kwargs: object) -> None:
                pass

            def handle_request(self) -> None:
                raise KeyboardInterrupt

            def server_close(self) -> None:
                close_count["value"] += 1

        monkeypatch.setattr(
            "providence_cli.commands.metrics.http.server.HTTPServer", FakeHTTPServer
        )
        for port in (9995, 9994, 9993):
            with pytest.raises(typer.Exit):
                serve(port=port, jsonl=metrics_events_path, refresh=1)
        assert close_count["value"] == 3

    def test_reload_worker_repeat_start_stop(self, metrics_events_path: Path) -> None:
        """Reload worker start/stop should be stable across repeated cycles."""
        from providence_runtime.metrics import TokenEconomyCollector
        from providence_runtime.reader import TelemetryReader

        for _ in range(5):
            collector = TokenEconomyCollector.from_reader(
                TelemetryReader(metrics_events_path)
            )
            collector_ref = _CollectorRef(collector)
            stop_event = threading.Event()
            worker = _start_reload_worker(
                jsonl_path=metrics_events_path,
                refresh=1,
                collector_ref=collector_ref,
                stop_event=stop_event,
            )
            stop_event.set()
            worker.join(timeout=2)
            assert not worker.is_alive()

    @pytest.mark.slow
    def test_serve_soak_restart_cycles(
        self, metrics_events_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Soak: repeated churn should exit cleanly with deterministic cleanup."""
        close_count = {"value": 0}
        cycles = 30

        class FakeHTTPServer:
            timeout = 1.0

            def __init__(self, *_args: object, **_kwargs: object) -> None:
                pass

            def handle_request(self) -> None:
                raise KeyboardInterrupt

            def server_close(self) -> None:
                close_count["value"] += 1

        monkeypatch.setattr(
            "providence_cli.commands.metrics.http.server.HTTPServer", FakeHTTPServer
        )
        for offset in range(cycles):
            with pytest.raises(typer.Exit):
                serve(port=9800 + offset, jsonl=metrics_events_path, refresh=1)

        assert close_count["value"] == cycles
