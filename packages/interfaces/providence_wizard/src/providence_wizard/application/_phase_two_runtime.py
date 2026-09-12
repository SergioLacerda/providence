"""Application boundary for the Phase 2 staging flow."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Protocol

from providence_wizard.orchestration.wizard.messages import phase2_instructions_message
from providence_wizard.orchestration.wizard.models import Phase2StageResult


class PhaseTwoContext(Protocol):
    """Narrow contract for delegating Phase 2 staging."""

    phase1_choices_dir: Path
    phase2_input_dir: Path
    wizard_config_path: Path
    SUPPORTED_PHASE2_PATTERNS: tuple[str, ...]
    _prompter: Any

    def _emit(self, message: str) -> None:
        """Send an operator-facing message."""


class PhaseTwoRuntime:
    """Application boundary for the Phase 2 staging flow."""

    def __init__(self, context: PhaseTwoContext) -> None:
        self._context = context

    def execute(self) -> Phase2StageResult:
        """Stage Phase 1 output into Phase 2 input and guide the operator."""
        phase1_path = self._context.phase1_choices_dir
        output_path = self._context.phase2_input_dir
        failed_status = self._load_failed_phase1_status()
        if failed_status is not None:
            return self._build_failed_status_result(
                phase1_path, output_path, failed_status
            )
        if not phase1_path.exists():
            self._context._emit(f"\n Phase 1 templates not found: {phase1_path}")
            self._context._emit("Run Phase 1 first to generate templates.")
            return self._build_missing_phase1_result(phase1_path, output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        copied_files = self._copy_supported_files(phase1_path, output_path)
        if not copied_files:
            return self._build_no_files_result(phase1_path, output_path)
        self._context._emit(
            phase2_instructions_message(phase1_path, output_path, copied_files)
        )
        return self._build_success(phase1_path, output_path, copied_files)

    def _load_failed_phase1_status(self) -> str | None:
        if not self._context.wizard_config_path.exists():
            return None
        try:
            with open(self._context.wizard_config_path, encoding="utf-8") as handle:
                config = json.load(handle)
        except (OSError, ValueError, TypeError) as exc:
            self._context._emit(
                f"  Unable to read phase1_status from {self._context.wizard_config_path}: {exc}"
            )
            return None
        phase1_status = config.get("phase1_status", {})
        if phase1_status.get("status") != "failed":
            return None
        return str(phase1_status.get("reason") or "unknown reason")

    def _copy_supported_files(self, phase1_path: Path, output_path: Path) -> list[str]:
        files_to_stage: dict[str, Path] = {}
        for pattern in self._context.SUPPORTED_PHASE2_PATTERNS:
            for input_file in sorted(phase1_path.glob(pattern)):
                files_to_stage[input_file.name] = input_file
        copied_files: list[str] = []
        for input_file in files_to_stage.values():
            destination = output_path / input_file.name
            shutil.copy2(input_file, destination)
            copied_files.append(input_file.name)
        return copied_files

    def _build_failed_status_result(
        self, phase1_path: Path, output_path: Path, reason: str
    ) -> Phase2StageResult:
        self._context._emit("\n Phase 1 did not complete successfully.")
        self._context._emit(f"Reason: {reason}")
        self._context._emit(
            "Run Phase 1 again after fixing the issue above before continuing."
        )
        return {
            "success": False,
            "phase1_path": str(phase1_path),
            "output_path": str(output_path),
            "copied_files": [],
            "error": f"Phase 1 status is failed: {reason}",
        }

    def _build_missing_phase1_result(
        self, phase1_path: Path, output_path: Path
    ) -> Phase2StageResult:
        return {
            "success": False,
            "phase1_path": str(phase1_path),
            "output_path": str(output_path),
            "copied_files": [],
            "error": "Phase 1 templates not found.",
        }

    def _build_no_files_result(
        self, phase1_path: Path, output_path: Path
    ) -> Phase2StageResult:
        self._context._emit(f"\n No supported review files found in: {phase1_path}")
        self._context._emit(
            f"Expected one of: {', '.join(self._context.SUPPORTED_PHASE2_PATTERNS)}"
        )
        self._context._emit("Run Phase 1 first to generate templates.")
        return {
            "success": False,
            "phase1_path": str(phase1_path),
            "output_path": str(output_path),
            "copied_files": [],
            "error": "No supported review files found in phase-1-choices.",
        }

    def _build_success(
        self, phase1_path: Path, output_path: Path, copied_files: list[str]
    ) -> Phase2StageResult:
        return {
            "success": True,
            "phase1_path": str(phase1_path),
            "output_path": str(output_path),
            "copied_files": copied_files,
            "error": "",
        }
