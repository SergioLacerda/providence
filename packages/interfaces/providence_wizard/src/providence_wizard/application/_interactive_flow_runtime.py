"""Application boundary for the single guided wizard flow (Scenario A/B).

Replaces the old "Choose Starting Phase" menu dispatch. Preferences and
agent/seedling selection are resolved once at the top (interactively or,
when `non_interactive`, without prompting  see `PreferencesFlow`), then the
flow branches exactly once on `custom_governance_path`:

- Scenario A (None): generate templates  stage  compile (Phase 1-3).
- Scenario B (set): validate + load the custom governance file, skipping
  Phase 1-3 entirely.

Both converge on Phase 4-6 project generation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Protocol

from providence_wizard.orchestration.custom_governance_loader import (
    load_custom_governance_file,
)
from providence_wizard.orchestration.wizard.models import (
    InteractivePhase3CompileResult,
    InteractivePhase4GenerateResult,
    Phase1GenerateResult,
    Phase2StageResult,
)


class InteractiveFlowContext(Protocol):
    """Narrow contract for the single guided wizard flow."""

    non_interactive: bool
    custom_governance_path: Path | None
    client_compiled_dir: Path

    def ask_user_preferences(self) -> dict[str, Any]:
        """Resolve preferences (prompts or non-interactive), cached."""

    def _ask_seedling_selection(self) -> set[str] | None:
        """Resolve agent/seedling selection (prompts or non-interactive), cached."""

    def _build_phase1_status(
        self, status: str, reason: str = "", artifacts: list[str] | None = None
    ) -> dict[str, Any]:
        """Build a phase1_status block for wizard-config.json."""

    def save_config(self, config: dict[str, Any]) -> Path:
        """Persist config to wizard-config.json."""

    def phase_1_generate_templates(self) -> Phase1GenerateResult:
        """Run Phase 1."""

    def phase_2_show_instructions(self) -> Phase2StageResult:
        """Run Phase 2 (auto-stage, no manual pause)."""

    def phase_3_compile_templates(self) -> InteractivePhase3CompileResult:
        """Run Phase 3."""

    def phase_4_generate_project(self) -> InteractivePhase4GenerateResult:
        """Run Phase 4-6."""

    def _emit(self, message: str) -> None:
        """Send an operator-facing message."""


class InteractiveFlowRuntime:
    """Application boundary for the single guided wizard flow."""

    def __init__(self, context: InteractiveFlowContext) -> None:
        self._context = context

    def execute(self) -> bool:
        """Run the single guided flow and translate wizard exceptions."""
        ctx = self._context
        try:
            if not self._can_proceed():
                return False

            ctx.ask_user_preferences()
            ctx._ask_seedling_selection()

            if ctx.custom_governance_path is not None:
                if not self._run_scenario_b():
                    return False
            elif not self._run_scenario_a():
                return False

            success = bool(ctx.phase_4_generate_project()["success"])
            if success:
                ctx._emit("--- WIZARD OK ---")
            return success
        except KeyboardInterrupt:
            ctx._emit("\n\n Wizard cancelled by user")
            return False
        except Exception as exc:
            ctx._emit(f"\n Error: {exc}")
            import traceback

            traceback.print_exc()
            return False

    def _can_proceed(self) -> bool:
        """Fail fast under non-interactive execution without a usable path."""
        ctx = self._context
        if ctx.non_interactive or ctx.custom_governance_path is not None:
            return True
        if sys.stdin.isatty():
            return True
        ctx._emit(
            "Wizard requires an interactive terminal, or --from-file for scripted use."
        )
        return False

    def _run_scenario_a(self) -> bool:
        """Generate templates, auto-stage, compile (Phase 1-3)."""
        ctx = self._context
        if not ctx.phase_1_generate_templates()["success"]:
            return False
        if not ctx.phase_2_show_instructions()["success"]:
            return False
        return bool(ctx.phase_3_compile_templates()["success"])

    def _run_scenario_b(self) -> bool:
        """Validate and stage the custom governance file; skip Phase 1-3."""
        ctx = self._context
        assert ctx.custom_governance_path is not None
        ok, errors = load_custom_governance_file(
            ctx.custom_governance_path, ctx.client_compiled_dir
        )
        if not ok:
            for error in errors:
                ctx._emit(f"   {error}")
            return False

        preferences = ctx.ask_user_preferences()
        config = {
            **preferences,
            "phase1_status": ctx._build_phase1_status(
                "skipped",
                "custom_governance_file",
                [str(ctx.custom_governance_path)],
            ),
        }
        ctx.save_config(config)
        return True
