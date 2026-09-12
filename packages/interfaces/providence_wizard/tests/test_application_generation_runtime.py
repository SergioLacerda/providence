"""Tests for Phase 3/4 application runtimes."""

from __future__ import annotations

from pathlib import Path

from providence_wizard.application.generation_runtime import (
    PhaseFourRuntime,
    PhaseThreeRuntime,
)


def test_phase_three_runtime_fails_when_phase2_input_missing(tmp_path: Path) -> None:
    context = _PhaseThreeContext(tmp_path)
    result = PhaseThreeRuntime(context).execute()
    assert result["success"] is False
    assert "Templates not found" in result["error"]


def test_phase_three_runtime_suppresses_detail_lines_by_default(
    tmp_path: Path,
) -> None:
    context = _PhaseThreeContext(tmp_path)
    runtime = PhaseThreeRuntime(context)
    runtime._emit_paths(tmp_path / "in", tmp_path / "out")
    assert context.messages == []


def test_phase_three_runtime_emits_detail_lines_when_debug(tmp_path: Path) -> None:
    context = _PhaseThreeContext(tmp_path)
    context.debug = True
    runtime = PhaseThreeRuntime(context)
    runtime._emit_paths(tmp_path / "in", tmp_path / "out")
    assert any(" Input" in message for message in context.messages)


def test_phase_three_runtime_suppresses_completion_block_by_default(
    tmp_path: Path,
) -> None:
    context = _PhaseThreeContext(tmp_path)
    runtime = PhaseThreeRuntime(context)

    result = runtime._handle_compiler_result(
        {
            "success": True,
            "output_path": str(tmp_path / "compiled"),
            "mandates": 1,
            "guidelines": 1,
            "files": [],
        },
        tmp_path / "compiled",
    )

    assert result["success"] is True
    assert not any("COMPLETE WIZARD FLOW" in message for message in context.messages)


def test_phase_three_runtime_emits_completion_block_when_debug(
    tmp_path: Path,
) -> None:
    context = _PhaseThreeContext(tmp_path)
    context.debug = True
    runtime = PhaseThreeRuntime(context)

    runtime._handle_compiler_result(
        {
            "success": True,
            "output_path": str(tmp_path / "compiled"),
            "mandates": 1,
            "guidelines": 1,
            "files": [],
        },
        tmp_path / "compiled",
    )

    assert any("COMPLETE WIZARD FLOW" in message for message in context.messages)


def test_phase_four_runtime_fails_without_config(tmp_path: Path) -> None:
    context = _PhaseFourContext(tmp_path)
    result = PhaseFourRuntime(context).execute()
    assert result["success"] is False
    assert "Configuration not found" in result["error"]


def test_phase_four_runtime_cleanup_is_compact_by_default(tmp_path: Path) -> None:
    context = _PhaseFourContext(tmp_path)
    context.cleaned = ["generated/client/build/phase-1-choices"]

    PhaseFourRuntime(context)._emit_cleanup()

    assert context.messages == ["cleanup...OK (1)"]


def test_phase_four_runtime_cleanup_lists_paths_when_debug(tmp_path: Path) -> None:
    context = _PhaseFourContext(tmp_path)
    context.debug = True
    context.cleaned = ["generated/client/build/phase-1-choices"]

    PhaseFourRuntime(context)._emit_cleanup()

    assert any("Cleaned temporary" in message for message in context.messages)
    assert any("phase-1-choices" in message for message in context.messages)


class _PhaseThreeContext:
    def __init__(self, tmp_path: Path) -> None:
        self.phase2_input_dir = tmp_path / "phase-2-input"
        self.client_compiled_dir = tmp_path / "compiled"
        self.paths = {"root": tmp_path}
        self.debug = False
        self.messages: list[str] = []

    def _emit(self, message: str) -> None:
        self.messages.append(message)

    def print_header(self, title: str, icon: str = "") -> None:
        self.messages.append(f"{icon} {title}")

    def phase_6_generate_seedlings(self, output_base: Path) -> bool:
        _ = output_base
        return True

    def _get_enforcement_label(self) -> str:
        return "Alertas"


class _PhaseFourContext:
    def __init__(self, tmp_path: Path) -> None:
        self.wizard_config_path = tmp_path / "wizard-config.json"
        self.client_compiled_dir = tmp_path / "compiled"
        self.final_template_dir = tmp_path / "final-template"
        self.paths = {"root": tmp_path}
        self.debug = False
        self.cleaned: list[str] = []
        self.messages: list[str] = []

    def _emit(self, message: str) -> None:
        self.messages.append(message)

    def _ask_seedling_selection(self) -> set[str] | None:
        return None

    def _consolidate_final_template(self) -> dict[str, object]:
        return {"success": True}

    def _cleanup_post_generation_artifacts(self) -> list[str]:
        return self.cleaned
