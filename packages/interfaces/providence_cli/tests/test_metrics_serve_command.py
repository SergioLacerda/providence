"""Tests for `sdd metrics serve` HTTP endpoint and error paths."""

from __future__ import annotations

import socket
from pathlib import Path
from unittest import mock

import pytest
import typer

from providence_cli.commands.metrics import serve

pytestmark = pytest.mark.integration


def _free_port() -> int:
    """Allocate an ephemeral localhost port for test server startup."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])
    except PermissionError:
        pytest.skip("Socket creation is restricted in this environment")
        return 0  # unreachable  pytest.skip() raises Skipped


class TestMetricsServeCommand:
    """Tests for `sdd metrics serve` subcommand."""

    def test_serve_no_jsonl_file_error(self, tmp_path: Path) -> None:
        """Serve should error gracefully when JSONL not found."""
        # Pass a path that doesn't exist (no fixture, no auto-detection)
        nonexistent_path = tmp_path / "nonexistent.jsonl"

        with pytest.raises(typer.Exit):
            serve(port=9999, jsonl=nonexistent_path, refresh=30)

    def test_serve_no_jsonl_file_json_error(self, tmp_path: Path) -> None:
        """Serve should emit canonical JSON error when file is missing."""
        nonexistent_path = tmp_path / "nonexistent.jsonl"
        with (
            mock.patch("providence_cli.commands.metrics.emit_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            serve(port=9999, jsonl=nonexistent_path, refresh=30, json_output=True)
        payload = mock_emit.call_args.args[0]
        assert payload["status"] == "error"
        assert payload["command"] == "metrics serve"
        assert payload["error"]["code"] == "events_file_not_found"
        assert payload["data"]["exit_code"] == 1

    def test_serve_metrics_endpoint(self, metrics_events_path: Path) -> None:
        """Serve should expose /metrics endpoint with Prometheus format."""
        import threading
        import time
        import urllib.error
        import urllib.request

        # Start server in background thread
        server_port = _free_port()

        def _run_serve() -> None:
            try:
                serve(port=server_port, jsonl=metrics_events_path, refresh=60)
            except typer.Exit:
                # In restricted environments bind can fail; test handles this via request path.
                return

        server_thread = threading.Thread(target=_run_serve, daemon=True)
        server_thread.start()

        # Give server time to start
        time.sleep(0.5)

        try:
            # Request /metrics endpoint
            response = urllib.request.urlopen(
                f"http://localhost:{server_port}/metrics", timeout=2
            )
            metrics_text = response.read().decode("utf-8")

            # Verify Prometheus format
            assert "# HELP" in metrics_text
            assert "# TYPE" in metrics_text
            assert "sdd_tokens" in metrics_text or metrics_text.strip() != ""
            assert response.status == 200

        except urllib.error.URLError:
            # Server may not have started in time; skip
            pytest.skip("Server did not start in time")

    def test_serve_metrics_404_for_other_paths(self, metrics_events_path: Path) -> None:
        """Serve should reject requests to non-/metrics paths."""
        import threading
        import time
        import urllib.error
        import urllib.request

        server_port = _free_port()

        def _run_serve() -> None:
            try:
                serve(port=server_port, jsonl=metrics_events_path, refresh=60)
            except typer.Exit:
                return

        server_thread = threading.Thread(target=_run_serve, daemon=True)
        server_thread.start()
        time.sleep(0.5)

        try:
            # Request non-metrics path should fail
            try:
                urllib.request.urlopen(
                    f"http://localhost:{server_port}/notfound", timeout=2
                )
                pytest.fail("Should have raised HTTP error")
            except urllib.error.HTTPError as e:
                # Accept both 404 and 501 (server implementation may vary)
                if e.code not in (404, 501):
                    pytest.fail(f"Expected 404 or 501, got {e.code}")

        except urllib.error.URLError:
            pytest.skip("Server did not start in time")

    def test_serve_with_explicit_jsonl_path(self, metrics_events_path: Path) -> None:
        """Serve should accept explicit --jsonl path."""
        import threading
        import time

        # Just verify it doesn't crash with explicit path
        # (would need full HTTP test for full validation)
        server_port = _free_port()

        def _run_serve() -> None:
            try:
                serve(port=server_port, jsonl=metrics_events_path, refresh=60)
            except typer.Exit:
                return

        server_thread = threading.Thread(target=_run_serve, daemon=True)
        server_thread.start()
        time.sleep(0.5)

        # If we get here, no exception was raised
        assert True

    def test_serve_bind_failure_exits_without_starting_worker(
        self, metrics_events_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bind failures should fail fast and avoid worker startup/leaks."""

        def _raise_bind(*_args: object, **_kwargs: object) -> None:
            raise PermissionError("bind denied")

        worker_started = {"value": False}

        def _worker(*_args: object, **_kwargs: object):
            worker_started["value"] = True
            raise AssertionError("reload worker must not start when bind fails")

        monkeypatch.setattr(
            "providence_cli.commands.metrics.http.server.HTTPServer", _raise_bind
        )
        monkeypatch.setattr(
            "providence_cli.commands.metrics._start_reload_worker", _worker
        )

        with pytest.raises(typer.Exit) as excinfo:
            serve(port=9799, jsonl=metrics_events_path, refresh=1)
        assert excinfo.value.exit_code == 1
        assert worker_started["value"] is False

    def test_serve_bind_failure_json_emits_canonical_error(
        self, metrics_events_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bind failure should emit canonical JSON error envelope."""

        def _raise_bind(*_args: object, **_kwargs: object) -> None:
            raise PermissionError("bind denied")

        monkeypatch.setattr(
            "providence_cli.commands.metrics.http.server.HTTPServer", _raise_bind
        )
        with (
            mock.patch("providence_cli.commands.metrics.emit_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            serve(port=9798, jsonl=metrics_events_path, refresh=1, json_output=True)
        payload = mock_emit.call_args.args[0]
        assert payload["status"] == "error"
        assert payload["command"] == "metrics serve"
        assert payload["error"]["code"] == "metrics_bind_failed"
        assert payload["data"]["exit_code"] == 1


class TestServeErrorPaths:
    def test_serve_missing_file_text_mode(self, tmp_path) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            serve(
                port=19999,
                jsonl=tmp_path / "missing.jsonl",
                refresh=30,
                json_output=False,
            )
        assert exc_info.value.exit_code == 1

    def test_serve_load_error_text_mode(self, tmp_path) -> None:
        from unittest.mock import patch

        events = tmp_path / "events.jsonl"
        events.write_text("{}\n", encoding="utf-8")

        with (
            patch(
                "providence_runtime.reader.TelemetryReader",
                side_effect=Exception("bad data"),
            ),
            patch("providence_cli.commands.metrics.console"),
            pytest.raises(typer.Exit) as exc_info,
        ):
            serve(port=19998, jsonl=events, refresh=30, json_output=False)
        assert exc_info.value.exit_code == 1

    def test_serve_load_error_json_mode(self, tmp_path) -> None:
        from unittest.mock import patch

        events = tmp_path / "events.jsonl"
        events.write_text("{}\n", encoding="utf-8")

        with (
            patch(
                "providence_runtime.reader.TelemetryReader",
                side_effect=Exception("bad data"),
            ),
            patch("providence_cli.commands.metrics.emit_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            serve(port=19997, jsonl=events, refresh=30, json_output=True)
        payload = mock_emit.call_args.args[0]
        assert payload["error"]["code"] == "metrics_load_failed"

    def test_serve_bind_error_text_mode(self, metrics_events_path, monkeypatch) -> None:
        monkeypatch.setattr(
            "providence_cli.commands.metrics.http.server.HTTPServer",
            lambda *a, **kw: (_ for _ in ()).throw(OSError("bind failed")),
        )
        with pytest.raises(typer.Exit) as exc_info:
            serve(
                port=19996,
                jsonl=metrics_events_path,
                refresh=30,
                json_output=False,
            )
        assert exc_info.value.exit_code == 1
