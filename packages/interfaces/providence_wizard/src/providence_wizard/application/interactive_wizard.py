#!/usr/bin/env python3
"""
Interactive mode for SDD Wizard v3 - Phase-based template generation

4-phase flow:
1. Phase 1: Generate markdown templates (asks: language, adoption_level)
2. Phase 2: Review + stage files into phase-2-input
3. Phase 3: Compile staged templates
4. Phase 4: Generate project structure
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from providence_core.utils.environment import get_sdd_paths
from providence_wizard.application.generation_runtime import (
    PhaseFourRuntime,
    PhaseThreeRuntime,
)
from providence_wizard.application.phase_runtime import (
    InteractiveFlowRuntime,
    PhaseOneRuntime,
    PhaseTwoRuntime,
)
from providence_wizard.application.preferences_flow import PreferencesFlow
from providence_wizard.application.prompter import Prompter, _wrap_prompter
from providence_wizard.application.seedling_bridge import SeedlingBridge
from providence_wizard.constants import (
    WIZARD_CONFIG_FILENAME as _WIZARD_CONFIG_FILENAME,
)
from providence_wizard.orchestration.wizard.models import (
    InteractivePhase3CompileResult as Phase3CompileResult,
)
from providence_wizard.orchestration.wizard.models import (
    InteractivePhase4GenerateResult as Phase4GenerateResult,
)
from providence_wizard.orchestration.wizard.models import (
    Phase1GenerateResult,
    Phase2StageResult,
)
from providence_wizard.orchestration.wizard.seedlings_runtime import (
    run_phase6_seedlings_generation,
)

from ._interactive_wizard_constants import (
    _ENFORCEMENT_CHOICES,
    _ENFORCEMENT_MAP,
    _FINAL_TEMPLATE_DIRNAME,
    _HANDSHAKE_CHOICES,
    _HANDSHAKE_MAP,
    _INTERACTION_LANGUAGE_CHOICES,
    _LOCAL_DOCS_LANGUAGE_CHOICES,
    _LOCALE_BY_LANGUAGE,
    _PHASE1_CHOICES_DIRNAME,
    _PHASE2_INPUT_DIRNAME,
)
from ._interactive_wizard_context_mixin import InteractiveWizardContextMixin


class InteractiveWizard(InteractiveWizardContextMixin):
    """Interactive guide for SDD Wizard v3"""

    SUPPORTED_PHASE2_PATTERNS: tuple[str, ...] = ("*.md", "*.spec", "*.dsl")

    def __init__(
        self,
        repo_root: Path,
        emitter: Callable[[str], None] | None = None,
        prompter: Prompter | Callable[[str], str] | None = None,
        output_dir: Path | None = None,
        non_interactive: bool = False,
        custom_governance_path: Path | None = None,
        debug: bool = False,
    ):
        paths = get_sdd_paths()
        self.repo_root = repo_root or paths["root"]
        self.paths = paths
        self._emit = emitter or print
        self._prompter = _wrap_prompter(prompter)
        self.non_interactive = non_interactive
        self.custom_governance_path = custom_governance_path
        self.debug = debug
        self._preferences_flow = PreferencesFlow(
            self._prompter, self._emit if self.debug else (lambda _message: None)
        )
        self._resolved_preferences: dict[str, Any] | None = None
        self._resolved_agent_selection: set[str] | None = None
        self._agent_selection_resolved = False
        self.config: dict[str, Any] = {}
        self.client_build_dir = self.paths["client_build"]
        self.client_compiled_dir = self.paths["client_compiled"]
        self.phase1_choices_dir = self.client_build_dir / _PHASE1_CHOICES_DIRNAME
        self.phase2_input_dir = self.client_build_dir / _PHASE2_INPUT_DIRNAME
        self.final_template_dir = (
            output_dir
            if output_dir is not None
            else self.client_build_dir / _FINAL_TEMPLATE_DIRNAME
        )
        self.wizard_config_path = self.client_build_dir / _WIZARD_CONFIG_FILENAME
        self.selector_output_path = self.client_build_dir / "selector-selection.json"
        self.selector_site_path = (
            self.repo_root / "build" / "site" / "selector" / "index.html"
        )

    def ask_user_preferences(self) -> dict[str, Any]:
        """Resolve user preferences: enforcement mode, language, and handshake mode.

        Resolved once and cached  safe to call multiple times (e.g. hoisted
        at the top of the flow, then again internally by PhaseOneRuntime)
        without prompting twice. When `non_interactive` is set, resolves
        without prompting at all (see `PreferencesFlow.resolve_non_interactive_preferences`).
        """
        if self._resolved_preferences is not None:
            return self._resolved_preferences

        if self.non_interactive:
            self._resolved_preferences = (
                self._preferences_flow.resolve_non_interactive_preferences(
                    self.client_build_dir
                )
            )
            return self._resolved_preferences

        if self.debug:
            self.print_header("User Preferences Setup", "")
        self._resolved_preferences = self._preferences_flow.collect_preferences(
            enforcement_choices=_ENFORCEMENT_CHOICES,
            enforcement_map=_ENFORCEMENT_MAP,
            interaction_language_choices=_INTERACTION_LANGUAGE_CHOICES,
            local_docs_language_choices=_LOCAL_DOCS_LANGUAGE_CHOICES,
            locale_by_language=_LOCALE_BY_LANGUAGE,
            handshake_choices=_HANDSHAKE_CHOICES,
            handshake_map=_HANDSHAKE_MAP,
        )
        return self._resolved_preferences

    def phase_1_generate_templates(self) -> Phase1GenerateResult:
        """Execute Phase 1: Generate templates with user preferences"""
        result = PhaseOneRuntime(self).execute()
        if result["success"]:
            self.config = json.loads(
                self.wizard_config_path.read_text(encoding="utf-8")
            )
        return result

    def phase_2_show_instructions(self) -> Phase2StageResult:
        """Show Phase 2 instructions and stage markdown files into phase-2-input."""
        return PhaseTwoRuntime(self).execute()

    def phase_3_compile_templates(self) -> Phase3CompileResult:
        """Execute Phase 3: Compile edited templates to governance JSON"""
        return PhaseThreeRuntime(self).execute()

    def phase_4_generate_project(self) -> Phase4GenerateResult:
        """Execute Phase 4-6: Generate project structure from compiled governance"""
        return PhaseFourRuntime(self).execute()

    def phase_6_generate_seedlings(self, output_base: Path) -> bool:
        """Execute Phase 6: Generate intelligent seedlings"""
        return SeedlingBridge().generate(
            wizard_config_path=self.wizard_config_path,
            output_base=output_base,
            emitter=self._emit,
            runner=run_phase6_seedlings_generation,
            debug=self.debug,
        )

    def run(self) -> bool:
        """Main interactive flow"""
        return InteractiveFlowRuntime(self).execute()


def run_interactive_wizard(
    repo_root: Path,
    output_dir: Path | None = None,
    non_interactive: bool = False,
    custom_governance_path: Path | None = None,
    debug: bool = False,
) -> bool:
    """Create an InteractiveWizard and run the main interactive flow."""
    return InteractiveWizard(
        repo_root=repo_root,
        output_dir=output_dir,
        non_interactive=non_interactive,
        custom_governance_path=custom_governance_path,
        debug=debug,
    ).run()
