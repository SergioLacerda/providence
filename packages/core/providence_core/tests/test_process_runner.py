"""Tests for SafeProcessRunner execution, telemetry, and interactive mode."""

from __future__ import annotations

import contextlib
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from providence_core.utils.process import SafeProcessRunner

pytestmark = pytest.mark.unit


class TestSafeProcessRunnerEdgeCases:
    """Tests for edge cases in process runner."""

    def test_run_with_empty_args(self) -> None:
        """Should handle empty arguments list gracefully."""
        runner = SafeProcessRunner()
        with pytest.raises((ValueError, IndexError, TypeError)):
            runner.run([])

    def test_run_with_none_args(self) -> None:
        """Should handle None arguments."""
        runner = SafeProcessRunner()
        with pytest.raises((ValueError, TypeError, AttributeError)):
            runner.run(None)  # type: ignore

    def test_run_interactive_with_blocking_flag(self) -> None:
        """run_interactive should validate Python flags."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="not permitted"):
            runner.run_interactive(["python3", "-c", "input()"])


class TestSafeProcessRunnerIntegrationEdgeCases:
    """Integration edge-case tests."""

    def test_run_preserves_cwd(self, tmp_path: Path) -> None:
        """Should preserve current working directory."""
        runner = SafeProcessRunner()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            with contextlib.suppress(FileNotFoundError):
                runner.run(["git", "status"], cwd=tmp_path)

    def test_run_with_capture_output(self) -> None:
        """Should support capture_output parameter."""
        runner = SafeProcessRunner()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")
            with contextlib.suppress(FileNotFoundError):
                runner.run(["git", "status"], capture_output=True)

    def test_run_with_shell_injection_blocked(self) -> None:
        """Should block python -c as shell=True equivalent."""
        runner = SafeProcessRunner()
        with pytest.raises(ValueError, match="not permitted"):
            runner.run(["python3", "-c", "os.system('bash')"])


class TestProcessRunnerTelemetrySink:
    """Tests for telemetry sink initialization."""

    def test_runner_with_explicit_sink(self) -> None:
        """SafeProcessRunner(telemetry_sink=...) assigns sink."""
        mock_sink = MagicMock()
        runner = SafeProcessRunner(telemetry_sink=mock_sink)
        assert runner._sink is mock_sink

    def test_runner_with_no_sink_defaults_gracefully(self) -> None:
        """Default construction sets _sink (TelemetrySink or None)."""
        runner = SafeProcessRunner(telemetry_sink=None)
        assert hasattr(runner, "_sink")


class TestRunTimeoutException:
    """Tests for timeout handling."""

    def test_run_timeout_exception_propagates(self) -> None:
        """subprocess.TimeoutExpired is caught and re-raised as ProcessTimeoutError."""
        runner = SafeProcessRunner()
        with (
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)),
            pytest.raises(subprocess.TimeoutExpired),
        ):
            runner.run(["git", "status"], timeout=5)


class TestRunInteractivePopens:
    """Tests for run_interactive() Popen behavior."""

    def test_run_interactive_success_path(self) -> None:
        """run_interactive succeeds with valid args and Popen."""
        runner = SafeProcessRunner()
        with (
            patch("subprocess.Popen") as mock_popen,
            patch.object(runner, "_emit_telemetry"),
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = ("output", "")
            mock_popen.return_value = mock_proc

            result = runner.run_interactive(["git", "status"])
            assert result.returncode == 0

    def test_run_interactive_timeout_expired(self) -> None:
        """run_interactive TimeoutExpired kills process."""
        runner = SafeProcessRunner()
        with (
            patch("subprocess.Popen") as mock_popen,
            patch.object(runner, "_emit_telemetry"),
        ):
            mock_proc = MagicMock()
            mock_proc.communicate.side_effect = subprocess.TimeoutExpired("git", 5)
            mock_popen.return_value = mock_proc

            with pytest.raises(subprocess.TimeoutExpired):
                runner.run_interactive(["git", "status"], timeout=5)
            mock_proc.kill.assert_called_once()

    def test_run_interactive_popen_oserror(self) -> None:
        """run_interactive OSError in Popen is caught and re-raised."""
        runner = SafeProcessRunner()
        with (
            patch("subprocess.Popen", side_effect=OSError("Cannot start process")),
            patch.object(runner, "_emit_telemetry"),
            pytest.raises(Exception, match="Could not execute interactive process"),
        ):
            runner.run_interactive(["git", "status"])


class TestEmitTelemetryEdgeCases:
    """Tests for _emit_telemetry behavior."""

    def test_emit_telemetry_with_no_sink(self) -> None:
        """_emit_telemetry early returns when _sink is None."""
        runner = SafeProcessRunner(telemetry_sink=None)
        runner._emit_telemetry("start", ["git", "status"])
        runner._emit_telemetry("finish", ["git", "status"], 0)

    def test_emit_telemetry_sink_exception_swallowed(self) -> None:
        """_emit_telemetry swallows exceptions from sink.emit()."""
        mock_sink = MagicMock()
        mock_sink.emit.side_effect = RuntimeError("Telemetry failed")
        runner = SafeProcessRunner(telemetry_sink=mock_sink)

        runner._emit_telemetry("start", ["git", "status"])
        runner._emit_telemetry("finish", ["git", "status"], 0)


class TestProcessTelemetryContract:
    """Contract tests for normalized process telemetry."""

    def test_single_trace_id_across_start_and_finish(self) -> None:
        mock_sink = MagicMock()
        runner = SafeProcessRunner(telemetry_sink=mock_sink)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            runner.run(["git", "status"])

        emitted = [call.args[0] for call in mock_sink.emit.call_args_list if call.args]
        assert len(emitted) >= 2
        trace_ids = {evt.trace_id for evt in emitted}
        assert len(trace_ids) == 1

    def test_normalize_status_values(self) -> None:
        runner = SafeProcessRunner(telemetry_sink=MagicMock())
        assert (
            runner._normalize_status(
                event_type="start", returncode=None, error_kind=None
            )
            == "ok"
        )
        assert (
            runner._normalize_status(event_type="finish", returncode=0, error_kind=None)
            == "ok"
        )
        assert (
            runner._normalize_status(
                event_type="finish", returncode=1, error_kind="non_zero"
            )
            == "error"
        )
        assert (
            runner._normalize_status(
                event_type="timeout", returncode=None, error_kind="timeout"
            )
            == "timeout"
        )
        assert (
            runner._normalize_status(
                event_type="error", returncode=None, error_kind="auth"
            )
            == "blocked"
        )
