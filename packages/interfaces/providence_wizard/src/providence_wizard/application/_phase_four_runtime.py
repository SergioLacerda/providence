"""Application boundary for the Phase 4-6 project generation flow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from providence_wizard.orchestration.wizard.messages import (
    phase4_consolidation_failed_message,
    phase4_success_message,
)
from providence_wizard.orchestration.wizard.models import (
    InteractivePhase4GenerateResult as Phase4GenerateResult,
)
from providence_wizard.orchestration.wizard.models import (
    build_interactive_phase4_result,
)

if TYPE_CHECKING:
    from providence_wizard.orchestration.wizard.models import (
        FinalTemplateConsolidationResult,
        Phase456RunResult,
    )


class PhaseFourContext(Protocol):
    """Narrow contract for Phase 4-6 project generation."""

    wizard_config_path: Path
    client_compiled_dir: Path
    final_template_dir: Path
    paths: dict[str, Any]
    debug: bool

    def _emit(self, message: str) -> None:
        """Send an operator-facing message."""

    def _ask_seedling_selection(self) -> set[str] | None:
        """Return selected seedlings or None for all."""

    def _consolidate_final_template(self) -> FinalTemplateConsolidationResult:
        """Consolidate compiled artifacts into final-template."""

    def _cleanup_post_generation_artifacts(self) -> list[str]:
        """Cleanup temporary onboarding artifacts."""


class PhaseFourRuntime:
    """Boundary for final project generation and consolidation."""

    def __init__(self, context: PhaseFourContext) -> None:
        self._context = context

    def execute(self) -> Phase4GenerateResult:
        """Generate project structure from compiled governance."""
        try:
            config = self._load_config()
            if config is None:
                return build_interactive_phase4_result(
                    success=False,
                    error="Configuration not found; run Phase 1 first.",
                )
            if not self._context.client_compiled_dir.exists():
                self._context._emit("\n Phase 3 output not found!")
                self._context._emit("You must run Phase 3 first to compile governance.")
                return build_interactive_phase4_result(
                    success=False,
                    error="Phase 3 output not found; run Phase 3 first.",
                )
            return self._run_generator(config)
        except Exception as exc:
            self._context._emit(f"\n Error: {exc}")
            import traceback

            traceback.print_exc()
            return build_interactive_phase4_result(success=False, error=str(exc))

    def _load_config(self) -> dict[str, Any] | None:
        if not self._context.wizard_config_path.exists():
            self._context._emit("\n Configuration not found!")
            self._context._emit("You must run Phase 1 first to set preferences.")
            return None
        with open(self._context.wizard_config_path, encoding="utf-8") as handle:
            config: dict[str, Any] = json.load(handle)
            return config

    def _run_generator(self, config: dict[str, Any]) -> Phase4GenerateResult:
        from providence_wizard.orchestration.phase_4_5_6_generator import (
            run_phase_4_5_6_generator,
        )

        result = run_phase_4_5_6_generator(
            self._context.paths["root"],
            self._context.client_compiled_dir,
            config,
            self._context._ask_seedling_selection(),
            debug=self._context.debug,
        )
        if not result["success"]:
            return self._build_failure(result)
        return self._build_success(result)

    def _build_failure(self, result: Phase456RunResult) -> Phase4GenerateResult:
        self._context._emit("\n Phase 4-6 generation failed!")
        for error in result.get("errors", []):
            self._context._emit(f"    {error}")
        error_messages = result.get("errors", [])
        return build_interactive_phase4_result(
            success=False,
            error="; ".join(error_messages)
            if error_messages
            else "Phase 4-6 generation failed.",
        )

    def _build_success(self, result: Phase456RunResult) -> Phase4GenerateResult:
        consolidation = self._context._consolidate_final_template()
        if not consolidation["success"]:
            self._context._emit(
                phase4_consolidation_failed_message(
                    self._context.client_compiled_dir, self._context.final_template_dir
                )
            )
            return build_interactive_phase4_result(
                success=False,
                mandates=int(result.get("mandates", 0)),
                guidelines=int(result.get("guidelines", 0)),
                categories=list(result.get("categories", [])),
                consolidated=False,
                error="Failed to consolidate final template bundle.",
            )
        self._context._emit(
            phase4_success_message(
                int(result["mandates"]),
                int(result["guidelines"]),
                list(result["categories"]),
                self._context.final_template_dir,
            )
        )
        self._emit_cleanup()
        return build_interactive_phase4_result(
            success=True,
            mandates=int(result.get("mandates", 0)),
            guidelines=int(result.get("guidelines", 0)),
            categories=list(result.get("categories", [])),
            consolidated=True,
        )

    def _emit_cleanup(self) -> None:
        cleaned = self._context._cleanup_post_generation_artifacts()
        if not cleaned:
            return
        if not self._context.debug:
            self._context._emit(f"cleanup...OK ({len(cleaned)})")
            return
        self._context._emit("   Cleaned temporary onboarding artifacts:")
        for relative_path in cleaned:
            self._context._emit(f"     - {relative_path}")
