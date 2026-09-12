"""Tests for providence_cli.services.governance_compile_handlers."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from rich.console import Console

from providence_cli.services.governance_compile_handlers import (
    resolve_output_base,
    run_compilation,
    run_compile,
)


def _console() -> Console:
    return Console(file=io.StringIO(), width=120)


class TestResolveOutputBase:
    def test_no_override_returns_resolved_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_TEST_OUTPUT_DIR", raising=False)
        assert resolve_output_base(tmp_path) == tmp_path.resolve()

    def test_override_with_resolve_workspace_root_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", str(tmp_path / "redirected"))
        with patch(
            "providence_cli.services.governance_compile_handlers.resolve_workspace_root",
            side_effect=RuntimeError("boom"),
        ):
            assert resolve_output_base(tmp_path) == tmp_path.resolve()

    def test_override_when_output_differs_from_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", str(tmp_path / "redirected"))
        other_ws = tmp_path / "other"
        with patch(
            "providence_cli.services.governance_compile_handlers.resolve_workspace_root",
            return_value=other_ws,
        ):
            assert resolve_output_base(tmp_path) == tmp_path.resolve()

    def test_override_when_output_matches_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        redirected = tmp_path / "redirected"
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", str(redirected))
        with patch(
            "providence_cli.services.governance_compile_handlers.resolve_workspace_root",
            return_value=tmp_path,
        ):
            result = resolve_output_base(tmp_path)
        assert result == redirected.resolve()
        assert redirected.exists()


class _FakeOrchestrator:
    _RESULT: dict | None = {"full_pipeline_success": True, "phase_1": {}, "phase_2": {}}

    def __init__(self, profile: str | None = None) -> None:
        self.profile = profile

    def run_full_pipeline(self):
        return self._RESULT


class TestRunCompilation:
    def test_success_returns_result(self) -> None:
        with patch(
            "providence_core.governance_orchestrator.GovernanceOrchestrator",
            _FakeOrchestrator,
        ):
            result = run_compilation(profile="client", console=_console())
        assert result["full_pipeline_success"] is True

    def test_default_console_created(self) -> None:
        with patch(
            "providence_core.governance_orchestrator.GovernanceOrchestrator",
            _FakeOrchestrator,
        ):
            result = run_compilation(profile=None)
        assert result["full_pipeline_success"] is True

    def test_failure_raises_exit(self) -> None:
        class _Failing(_FakeOrchestrator):
            _RESULT = {"full_pipeline_success": False}

        with (
            patch(
                "providence_core.governance_orchestrator.GovernanceOrchestrator",
                _Failing,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_compilation(profile=None, console=_console())
        assert exc_info.value.exit_code == 1

    def test_empty_result_raises_exit(self) -> None:
        class _Empty(_FakeOrchestrator):
            _RESULT = {}

        with (
            patch(
                "providence_core.governance_orchestrator.GovernanceOrchestrator", _Empty
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_compilation(profile=None, console=_console())
        assert exc_info.value.exit_code == 1


class TestRunCompile:
    def _success_patches(self):
        return (
            patch(
                "providence_cli.services.governance_compile_handlers.run_compilation",
                return_value={
                    "phase_1": {"core_fingerprint": "a" * 64},
                    "phase_2": {},
                },
            ),
            patch(
                "providence_cli.services.governance_compile_handlers.update_profile_hash"
            ),
            patch(
                "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
                return_value=(True, ""),
            ),
            patch(
                "providence_cli.services.governance_artifact_handlers.run_governance_compile_json",
                return_value=(
                    {
                        "status": "ok",
                        "ok": True,
                        "command": "governance compile",
                        "error": None,
                        "data": {},
                    },
                    False,
                ),
            ),
            patch(
                "providence_cli.services.governance_command_output.render_governance_compile_table"
            ),
            patch(
                "providence_cli.services.governance_compile_handlers.emit_compile_telemetry"
            ),
            patch(
                "providence_cli.services.governance_compile_handlers.regenerate_seeds"
            ),
            patch(
                "providence_cli.utils.providence_authority.resolve_workspace_root",
                return_value=Path("/tmp/ws"),
            ),
        )

    def test_invalid_profile_raises_exit(self) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            run_compile(profile="bogus", output_json=False, console=_console())
        assert exc_info.value.exit_code == 1

    def test_default_console_created(self) -> None:
        from contextlib import ExitStack

        with ExitStack() as stack:
            for p in self._success_patches():
                stack.enter_context(p)
            run_compile(profile=None, output_json=False, console=None)

    def test_valid_profile_success(self) -> None:
        from contextlib import ExitStack

        with ExitStack() as stack:
            for p in self._success_patches():
                stack.enter_context(p)
            run_compile(profile="client", output_json=False, console=_console())
