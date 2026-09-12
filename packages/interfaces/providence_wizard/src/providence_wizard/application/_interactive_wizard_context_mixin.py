"""Thin wiring methods shared by InteractiveWizard, called back into by the
phase-runtime classes (PhaseOneRuntime, PhaseThreeRuntime, PhaseFourRuntime,
etc.) via `self._context.<method>()`. Split out of interactive_wizard.py to
keep that file under the 200-line convention; behavior is unchanged  these
remain regular instance methods via mixin inheritance.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from providence_wizard.application.operator_state import read_enforcement_label
from providence_wizard.application.prompter import Prompter
from providence_wizard.application.workspace_runtime import (
    build_selector_discovery_config,
    build_selector_selection_config,
    cleanup_post_generation_artifacts,
    docs_meta_ready,
    emit_selector_phase1_hint,
    ensure_onboarding_scaffold,
    load_selector_selection_ids,
    source_spec_ready,
)
from providence_wizard.orchestration.wizard.final_template_bundle import (
    consolidate_final_template,
)
from providence_wizard.orchestration.wizard.models import (
    FinalTemplateConsolidationResult,
)
from providence_wizard.orchestration.wizard.seedling_selection import (
    ask_seedling_selection,
)

from ._interactive_wizard_constants import (
    _ONBOARDING_BASELINE_GUIDELINES,
    _ONBOARDING_BASELINE_MANDATE,
    _TEMP_BUILD_DIRS,
    _TEMP_COMPILED_DIRS,
)
from ._interactive_wizard_helpers import (
    _build_phase1_status,
    _do_consolidate_final_template,
    _ensure_docs_meta_ready,
    _save_config,
)


class InteractiveWizardContextMixin:
    """Selector wiring, config persistence, and scaffold helpers for the wizard.

    Always mixed into InteractiveWizard, never instantiated standalone  the
    attributes below are declared (not assigned) so mypy can type-check the
    methods that reference them; actual values come from
    InteractiveWizard.__init__.
    """

    repo_root: Path
    paths: dict[str, Path]
    _emit: Callable[[str], None]
    _prompter: Prompter
    non_interactive: bool
    debug: bool
    client_build_dir: Path
    client_compiled_dir: Path
    phase1_choices_dir: Path
    phase2_input_dir: Path
    final_template_dir: Path
    wizard_config_path: Path
    selector_output_path: Path
    selector_site_path: Path
    _resolved_agent_selection: set[str] | None
    _agent_selection_resolved: bool

    def load_selector_selection_ids(
        self,
        selection_path: Path | None = None,
        *,
        available_ids: set[str] | None = None,
    ) -> list[str]:
        """Load selector IDs when a selection artifact is present."""
        return load_selector_selection_ids(
            selection_path or self.selector_output_path,
            available_ids=available_ids,
        )

    def _load_selector_selection_config(self) -> dict[str, Any]:
        """Return selector selection metadata when an export artifact exists."""
        return build_selector_selection_config(self.selector_output_path)

    def _emit_selector_phase1_hint(self, selector_selection: dict[str, Any]) -> None:
        """Emit an optional selector hint without changing phase semantics."""
        if not self.debug:
            return
        emit_selector_phase1_hint(
            self._emit,
            selector_output_path=self.selector_output_path,
            selector_site_path=self.selector_site_path,
            selector_selection=selector_selection,
        )

    def _build_selector_discovery_config(
        self, selector_selection: dict[str, Any]
    ) -> dict[str, Any]:
        """Persist selector discovery context for auditability."""
        return build_selector_discovery_config(
            selector_output_path=self.selector_output_path,
            selector_site_path=self.selector_site_path,
            selector_selection=selector_selection,
        )

    def _consolidate_final_template(self) -> FinalTemplateConsolidationResult:
        """Move all compiled artifacts into build/final-template for user handoff."""
        return _do_consolidate_final_template(
            self.client_compiled_dir,
            self.final_template_dir,
            self._emit if self.debug else (lambda _message: None),
            consolidate_final_template,
        )

    def print_header(self, title: str, icon: str = "") -> None:
        """Print formatted header"""
        self._emit(f"\n{icon} {title}")
        self._emit("=" * 70)

    def save_config(self, config: dict[str, Any]) -> Path:
        """Save configuration to wizard-config.json"""
        return _save_config(self.client_build_dir, self.wizard_config_path, config)

    def _build_phase1_status(
        self, status: str, reason: str = "", artifacts: list[str] | None = None
    ) -> dict[str, Any]:
        """Build phase-1 status block persisted to wizard-config.json."""
        return _build_phase1_status(status, reason, artifacts)

    def _ensure_onboarding_scaffold(self) -> tuple[bool, str]:
        """Create minimal wizard scaffold for first-run onboarding."""
        return ensure_onboarding_scaffold(
            client_build_dir=self.client_build_dir,
            phase1_choices_dir=self.phase1_choices_dir,
            phase2_input_dir=self.phase2_input_dir,
            baseline_mandate=_ONBOARDING_BASELINE_MANDATE,
            baseline_guidelines=_ONBOARDING_BASELINE_GUIDELINES,
            emit=self._emit,
        )

    def _ensure_docs_meta_ready(self) -> tuple[bool, str]:
        """Ensure Phase 1 inputs exist (legacy docs-meta or unified source_spec)."""
        scaffold_ok, scaffold_reason = self._ensure_onboarding_scaffold()
        return _ensure_docs_meta_ready(
            scaffold_ok,
            scaffold_reason,
            docs_meta_ready(self.client_build_dir),
            source_spec_ready(self.paths, self.client_build_dir),
            self.client_build_dir,
            self.paths,
        )

    def _ask_seedling_selection(self) -> set[str] | None:
        """Resolve which seedlings to include. Returns None for all.

        Resolved once and cached  safe to call multiple times without
        prompting twice. When `non_interactive` is set, resolves to `None`
        (all seedlings) without prompting.
        """
        if self._agent_selection_resolved:
            return self._resolved_agent_selection

        if self.non_interactive:
            self._resolved_agent_selection = None
        else:
            emitter = self._emit if self.debug else (lambda _message: None)
            self._resolved_agent_selection = ask_seedling_selection(
                emitter, prompter=self._prompter
            )
        self._agent_selection_resolved = True
        return self._resolved_agent_selection

    def _cleanup_post_generation_artifacts(self) -> list[str]:
        """Remove wizard temporary artifacts while preserving final-template."""
        return cleanup_post_generation_artifacts(
            repo_root=self.repo_root,
            client_build_dir=self.client_build_dir,
            client_compiled_dir=self.client_compiled_dir,
            final_template_dir=self.final_template_dir,
            wizard_config_path=self.wizard_config_path,
            temp_build_dirs=_TEMP_BUILD_DIRS,
            temp_compiled_dirs=_TEMP_COMPILED_DIRS,
        )

    def _get_enforcement_label(self) -> str:
        """Get enforcement mode label from config"""
        return read_enforcement_label(self.wizard_config_path)
