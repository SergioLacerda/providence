"""Tests for governance_command_output presentation helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import typer
from rich.console import Console

from providence_cli.services.governance_command_output import (
    fail_generate_precondition,
    handle_compile_output,
)

pytestmark = pytest.mark.unit


class TestHandleCompileOutput:
    def _make_console(self) -> Console:
        return Console(file=MagicMock(), highlight=False)

    def test_json_mode_success_emits_json_and_returns(self) -> None:
        payload = {"status": "ok"}
        with patch(
            "providence_cli.services.governance_command_output.emit_json"
        ) as mock_emit:
            handle_compile_output(
                output_json=True,
                payload=payload,
                is_error=False,
                phase_1={},
                phase_2={},
                core_fingerprint="fp-1",
                consistency_reason="",
                console=self._make_console(),
            )
        mock_emit.assert_called_once_with(payload, err=False)

    def test_json_mode_error_emits_json_and_exits(self) -> None:
        payload = {"status": "error"}
        with (
            patch("providence_cli.services.governance_command_output.emit_json"),
            pytest.raises(typer.Exit) as exc_info,
        ):
            handle_compile_output(
                output_json=True,
                payload=payload,
                is_error=True,
                phase_1={},
                phase_2={},
                core_fingerprint="fp-1",
                consistency_reason="mismatch",
                console=self._make_console(),
            )
        assert exc_info.value.exit_code == 1

    def test_text_mode_error_prints_and_exits(self, capsys) -> None:
        console = Console()
        with pytest.raises(typer.Exit) as exc_info:
            handle_compile_output(
                output_json=False,
                payload={},
                is_error=True,
                phase_1={},
                phase_2={},
                core_fingerprint="fp-1",
                consistency_reason="fingerprint mismatch",
                console=console,
                artifact_path="/workspace/.providence/compiled",
            )
        assert exc_info.value.exit_code == 1
        captured = capsys.readouterr().out
        lines = [line for line in captured.splitlines() if line.strip()]
        assert len(lines) <= 3
        assert "fingerprint mismatch" in captured
        assert "artifact=/workspace/.providence/compiled" in captured
        assert "next=providence governance validate" in captured

    def test_text_mode_success_calls_render_table(self) -> None:
        console = self._make_console()
        with patch(
            "providence_cli.services.governance_command_output.render_governance_compile_table"
        ) as mock_render:
            handle_compile_output(
                output_json=False,
                payload={},
                is_error=False,
                phase_1={"key": "v1"},
                phase_2={"key": "v2"},
                core_fingerprint="fp-abc",
                consistency_reason="",
                console=console,
            )
        mock_render.assert_called_once_with(
            console=console,
            phase_1={"key": "v1"},
            phase_2={"key": "v2"},
            core_fingerprint="fp-abc",
        )


class TestFailGeneratePrecondition:
    def test_json_mode_emits_error_result_and_exits(self) -> None:
        console = Console(file=MagicMock(), highlight=False)
        with (
            patch(
                "providence_cli.services.governance_command_output.emit_json"
            ) as mock_emit,
            pytest.raises(typer.Exit) as exc_info,
        ):
            fail_generate_precondition(
                output_json=True,
                code="missing_config",
                message="Config not found",
                data={"detail": "x"},
                console=console,
            )
        assert exc_info.value.exit_code == 1
        mock_emit.assert_called_once()
        payload = mock_emit.call_args[0][0]
        assert payload["status"] == "error"

    def test_text_mode_prints_error_and_exits(self, capsys) -> None:
        console = Console()
        with pytest.raises(typer.Exit) as exc_info:
            fail_generate_precondition(
                output_json=False,
                code="missing_config",
                message="Config not found",
                data={"resolved_path": "/workspace/.providence"},
                console=console,
            )
        assert exc_info.value.exit_code == 1
        captured = capsys.readouterr().out
        lines = [line for line in captured.splitlines() if line.strip()]
        assert len(lines) <= 2
        assert "Config not found" in captured
        assert "artifact=/workspace/.providence" in captured
