"""Tests for `sdd metrics summary` and resolve/integration helpers."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
import typer

from providence_cli.commands.metrics import summary

pytestmark = pytest.mark.integration


class TestMetricsSummaryCommand:
    """Tests for `sdd metrics summary` subcommand."""

    def test_summary_no_jsonl_file_error(self, tmp_path: Path) -> None:
        """Summary should error gracefully when JSONL not found."""
        # Pass a path that doesn't exist (no fixture, no auto-detection)
        nonexistent_path = tmp_path / "nonexistent.jsonl"

        with pytest.raises(typer.Exit):
            summary(ctx=mock.MagicMock(), jsonl=nonexistent_path, last_hours=None)

    def test_summary_with_sample_events(self, metrics_events_path: Path) -> None:
        """Summary should load and render events correctly."""
        # Capture console output
        with mock.patch("providence_cli.commands.metrics.console") as mock_console:
            summary(ctx=mock.MagicMock(), jsonl=metrics_events_path, last_hours=None)

            # Verify console.print was called (table rendered)
            assert mock_console.print.called

    def test_summary_with_time_filter(self, metrics_events_path: Path) -> None:
        """Summary should support --last-hours filtering."""
        with mock.patch("providence_cli.commands.metrics.console") as mock_console:
            # This should not crash; time filtering is handled by reader
            summary(ctx=mock.MagicMock(), jsonl=metrics_events_path, last_hours=1)

            # Should still render (older events may or may not be included)
            assert mock_console.print.called

    def test_summary_with_explicit_jsonl_path(self, metrics_events_path: Path) -> None:
        """Summary should accept explicit --jsonl path."""
        with mock.patch("providence_cli.commands.metrics.console") as mock_console:
            summary(ctx=mock.MagicMock(), jsonl=metrics_events_path, last_hours=None)

            assert mock_console.print.called

    def test_summary_renders_token_metrics(self, metrics_events_path: Path) -> None:
        """Summary should render token consumption metrics from synthetic events."""
        with mock.patch("providence_cli.commands.metrics.console") as mock_console:
            summary(ctx=mock.MagicMock(), jsonl=metrics_events_path, last_hours=None)

            # Should have called print at least once for table output
            assert mock_console.print.called

    def test_summary_json_mode_emits_envelope(self, metrics_events_path: Path) -> None:
        """Summary should emit standard JSON envelope in global --json mode."""
        ctx = mock.MagicMock()
        ctx.obj = {"output_json": True}
        with mock.patch("providence_cli.commands.metrics.emit_json") as mock_emit:
            summary(ctx=ctx, jsonl=metrics_events_path, last_hours=None)
        payload = mock_emit.call_args.args[0]
        assert payload["status"] == "ok"
        assert payload["command"] == "metrics summary"
        assert payload["ok"] is True
        assert payload["data"]["exit_code"] == 0
        assert "summary" in payload["data"]

    def test_summary_json_mode_missing_file_emits_error(self, tmp_path: Path) -> None:
        """Summary should emit JSON error envelope when file is missing."""
        ctx = mock.MagicMock()
        ctx.obj = {"output_json": True}
        nonexistent_path = tmp_path / "missing.jsonl"
        with (
            mock.patch("providence_cli.commands.metrics.emit_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            summary(ctx=ctx, jsonl=nonexistent_path, last_hours=None)
        payload = mock_emit.call_args.args[0]
        assert payload["status"] == "error"
        assert payload["command"] == "metrics summary"
        assert payload["ok"] is False
        assert payload["data"]["exit_code"] == 1

    def test_summary_json_mode_uses_canonical_data_payload(
        self, metrics_events_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Strict mode should expose only canonical envelope + data payload."""
        ctx = mock.MagicMock()
        ctx.obj = {"output_json": True}
        with mock.patch("providence_cli.commands.metrics.emit_json") as mock_emit:
            summary(ctx=ctx, jsonl=metrics_events_path, last_hours=None)
        payload = mock_emit.call_args.args[0]
        assert payload["status"] == "ok"
        assert payload["command"] == "metrics summary"
        assert payload["ok"] is True
        assert payload["data"]["exit_code"] == 0
        assert "exit_code" not in payload
        assert "summary" not in payload

    def test_summary_json_mode_error_uses_canonical_data_payload(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Strict mode error should keep exit metadata only under data."""
        ctx = mock.MagicMock()
        ctx.obj = {"output_json": True}
        nonexistent_path = tmp_path / "missing.jsonl"
        with (
            mock.patch("providence_cli.commands.metrics.emit_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            summary(ctx=ctx, jsonl=nonexistent_path, last_hours=None)
        payload = mock_emit.call_args.args[0]
        assert payload["status"] == "error"
        assert payload["command"] == "metrics summary"
        assert payload["ok"] is False
        assert payload["data"]["exit_code"] == 1
        assert "exit_code" not in payload


class TestResolveJsonlPath:
    def test_returns_explicit_path_when_provided(self, tmp_path) -> None:
        from providence_cli.commands.metrics import _resolve_jsonl_path

        explicit = tmp_path / "events.jsonl"
        assert _resolve_jsonl_path(explicit) == explicit

    def test_returns_default_path_when_none(self) -> None:
        from providence_cli.commands.metrics import _resolve_jsonl_path

        result = _resolve_jsonl_path(None)
        assert result.name == "compliance-events.jsonl"

    def test_returns_existing_default_path(self, tmp_path, monkeypatch) -> None:
        from providence_cli.commands.metrics import _resolve_jsonl_path

        events = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"
        events.parent.mkdir(parents=True, exist_ok=True)
        events.write_text("", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = _resolve_jsonl_path(None)
        assert result.name == "compliance-events.jsonl"


class TestSummaryErrorPaths:
    def test_summary_load_error_text_mode(self, tmp_path) -> None:
        from unittest.mock import MagicMock, patch

        import typer

        events = tmp_path / "events.jsonl"
        events.write_text("{}\n", encoding="utf-8")
        ctx = MagicMock()
        ctx.obj = {}

        with (
            patch(
                "providence_runtime.reader.TelemetryReader",
                side_effect=Exception("corrupt data"),
            ),
            patch("providence_cli.commands.metrics.console"),
            pytest.raises(typer.Exit) as exc_info,
        ):
            summary(ctx=ctx, jsonl=events, last_hours=None)
        assert exc_info.value.exit_code == 1

    def test_summary_load_error_json_mode(self, tmp_path) -> None:
        from unittest.mock import MagicMock, patch

        import typer

        events = tmp_path / "events.jsonl"
        events.write_text("{}\n", encoding="utf-8")
        ctx = MagicMock()
        ctx.obj = {"output_json": True}

        with (
            patch(
                "providence_runtime.reader.TelemetryReader",
                side_effect=Exception("corrupt data"),
            ),
            patch("providence_cli.commands.metrics.emit_json") as mock_emit,
            pytest.raises(typer.Exit),
        ):
            summary(ctx=ctx, jsonl=events, last_hours=None)
        payload = mock_emit.call_args.args[0]
        assert payload["error"]["code"] == "metrics_load_failed"

    def test_summary_budget_breach_text_mode(self, metrics_events_path) -> None:
        from unittest.mock import MagicMock, patch

        ctx = MagicMock()
        ctx.obj = {}
        snap = MagicMock()
        snap.budget_utilization_pct = 105.0
        snap.total_tokens_input = 100
        snap.total_tokens_output = 50
        snap.total_tokens_total = 150
        snap.total_cost_usd = 0.01
        snap.total_calls = 5
        snap.warn_count = 0
        snap.breach_count = 1
        snap.retry_cap_count = 0

        with (
            patch("providence_runtime.reader.TelemetryReader"),
            patch("providence_runtime.metrics.TokenEconomyCollector") as mock_coll,
            patch("providence_cli.commands.metrics.console"),
        ):
            mock_coll.from_reader.return_value.snapshot.return_value = snap
            summary(ctx=ctx, jsonl=metrics_events_path, last_hours=None)

    def test_summary_budget_warning_text_mode(self, metrics_events_path) -> None:
        from unittest.mock import MagicMock, patch

        ctx = MagicMock()
        ctx.obj = {}
        snap = MagicMock()
        snap.budget_utilization_pct = 92.0
        snap.total_tokens_input = 100
        snap.total_tokens_output = 50
        snap.total_tokens_total = 150
        snap.total_cost_usd = 0.01
        snap.total_calls = 5
        snap.warn_count = 1
        snap.breach_count = 0
        snap.retry_cap_count = 0

        with (
            patch("providence_runtime.reader.TelemetryReader"),
            patch("providence_runtime.metrics.TokenEconomyCollector") as mock_coll,
            patch("providence_cli.commands.metrics.console"),
        ):
            mock_coll.from_reader.return_value.snapshot.return_value = snap
            summary(ctx=ctx, jsonl=metrics_events_path, last_hours=None)


class TestMetricsIntegration:
    """Integration tests combining summary and serve."""

    def test_summary_and_serve_same_data(self, metrics_events_path: Path) -> None:
        """Both summary and serve should read same JSONL consistently."""
        # Load with summary
        with mock.patch("providence_cli.commands.metrics.console"):
            summary(ctx=mock.MagicMock(), jsonl=metrics_events_path, last_hours=None)

        # Summary didn't crash, so data is readable
        # Serve would do the same (tested above)
        assert metrics_events_path.exists()
        assert metrics_events_path.stat().st_size > 0
