"""Tests for providence_cli.services.governance_artifact_handlers  output/JSON helpers."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from rich.console import Console

from providence_cli.services.governance_artifact_handlers import (
    emit_generate_invalid_path_error,
    emit_generate_missing_items_error,
    render_generate_table,
    render_governance_compile_table,
    run_governance_compile_json,
    run_governance_generate_json,
)


def _console() -> Console:
    return Console(file=io.StringIO(), width=120)


class TestRunGovernanceCompileJson:
    def test_consistency_failure_returns_error_payload(self) -> None:
        payload, is_error = run_governance_compile_json(
            phase_1={"core_item_count": 5, "client_item_count": 2},
            phase_2={
                "core_msgpack_file": "core.msgpack",
                "client_msgpack_file": "client.msgpack",
            },
            core_fingerprint="abc123",
            consistency_ok=False,
            consistency_reason="boom",
        )
        assert is_error is True
        assert payload["ok"] is False
        assert payload["error"]["code"] == "artifact_consistency_failed"
        assert "boom" in payload["error"]["message"]
        assert payload["data"]["exit_code"] == 1

    def test_consistency_success_returns_ok_payload(self) -> None:
        payload, is_error = run_governance_compile_json(
            phase_1={"core_item_count": 5, "client_item_count": 2},
            phase_2={
                "core_msgpack_file": "core.msgpack",
                "client_msgpack_file": "client.msgpack",
            },
            core_fingerprint="abc123",
            consistency_ok=True,
            consistency_reason="ok",
        )
        assert is_error is False
        assert payload["ok"] is True
        assert payload["data"]["exit_code"] == 0


class TestRenderGovernanceCompileTable:
    def test_renders_expected_rows(self) -> None:
        console = _console()
        render_governance_compile_table(
            console=console,
            phase_1={"core_item_count": 3, "client_item_count": 1},
            phase_2={
                "core_msgpack_file": "core.msgpack",
                "client_msgpack_file": "client.msgpack",
            },
            core_fingerprint="abc123",
        )
        output = console.file.getvalue()
        assert "Compilation Summary" in output
        assert "Core items" in output
        assert "core.msgpack" in output


class TestRunGovernanceGenerateJson:
    def test_returns_ok_payload(self, tmp_path: Path) -> None:
        payload = run_governance_generate_json(
            resolved_path=str(tmp_path),
            output_base=tmp_path,
            seeds_dir=tmp_path / "seeds",
            rows=[{"agent_template": "copilot", "location": "x", "status": "ok"}],
            skills_generated=True,
            skill_index_generated=True,
            cli_index_generated=False,
        )
        assert payload["ok"] is True
        assert payload["data"]["exit_code"] == 0


class TestEmitGenerateInvalidPathError:
    def test_emits_error_and_exits(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_cli.services.governance_artifact_handlers.emit_json"
            ) as mock_emit,
            pytest.raises(typer.Exit) as exc_info,
        ):
            emit_generate_invalid_path_error(
                resolved_path=str(tmp_path), output_dir=str(tmp_path)
            )
        assert exc_info.value.exit_code == 1
        mock_emit.assert_called_once()
        payload, kwargs = mock_emit.call_args
        assert payload[0]["error"]["code"] == "invalid_governance_path"
        assert kwargs["err"] is True


class TestEmitGenerateMissingItemsError:
    def test_emits_error_and_exits(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_cli.services.governance_artifact_handlers.emit_json"
            ) as mock_emit,
            pytest.raises(typer.Exit) as exc_info,
        ):
            emit_generate_missing_items_error(
                resolved_path=str(tmp_path), output_dir=str(tmp_path)
            )
        assert exc_info.value.exit_code == 1
        mock_emit.assert_called_once()
        payload, kwargs = mock_emit.call_args
        assert payload[0]["error"]["code"] == "missing_governance_items"
        assert kwargs["err"] is True


class TestRenderGenerateTable:
    def test_renders_rows_and_panel(self, tmp_path: Path) -> None:
        console = _console()
        rows = [{"agent_template": "copilot", "location": "x.md", "status": "ok"}]
        render_generate_table(console=console, rows=rows, seeds_dir=tmp_path)
        output = console.file.getvalue()
        assert "Generated Files" in output
        assert "copilot" in output
        assert "Agent seeds generated to" in output
