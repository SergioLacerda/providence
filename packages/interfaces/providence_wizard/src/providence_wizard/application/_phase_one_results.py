"""Result-builder helpers for PhaseOneRuntime."""

from __future__ import annotations

from typing import Any

from providence_wizard.orchestration.wizard.models import Phase1GenerateResult


def build_phase1_failure(
    *,
    phase1_choices_dir: str,
    error: str,
    config_path: str,
    config: dict[str, Any] | None = None,
) -> Phase1GenerateResult:
    active_config = config or {}
    return {
        "success": False,
        "config_path": config_path,
        "output_path": phase1_choices_dir,
        "language": str(active_config.get("language", "Python")),
        "enforcement_mode": str(active_config.get("enforcement_mode", "warn_mode")),
        "error": error,
    }


def build_phase1_result(
    *,
    success: bool,
    config_path: str,
    output_path: str,
    config: dict[str, Any],
) -> Phase1GenerateResult:
    return {
        "success": success,
        "config_path": config_path,
        "output_path": output_path,
        "language": str(config.get("language", "Python")),
        "enforcement_mode": str(config.get("enforcement_mode", "warn_mode")),
        "error": "",
    }
