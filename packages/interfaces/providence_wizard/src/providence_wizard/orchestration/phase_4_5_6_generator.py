"""
Phase 4-6 Generator for SDD Wizard v3

Phase 4: Load governance JSON + apply templates
Phase 5: Generate directory structure + organize by category + copy files
Phase 6: Validate output + create manifest

Output Structure (AI Agent Optimized):
.providence/
 source/                    (Unique source of truth for agent queries)
    mandates/
       mandates.md       (Compiled, IA-FIRST optimized)
    guidelines/
       git.md
       testing.md
       naming.md
       docs.md
       style.md
       performance.md
    README.md             (Agent instructions)
 runtime/
    README.md             (Pre-cache instructions for agents)
 metadata.json

.github/workflows/
 sdd-validation.yml

.vscode/, .cursor/ (seedlings with references to .providence/source)
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from providence_core.utils.environment import get_sdd_paths
from providence_wizard.constants import RUNTIME_DIRNAME

from ._phase456_governance_io import _resolve_governance_inputs
from ._phase456_pipeline_steps import (
    _create_source_directories,
    _generate_plugin_workspace_dirs,
)
from ._phase456_run import run_phase456_pipeline
from ._phase456_source_writer import write_phase5_sources
from .phase6_seedlings_orchestrator import SeedlingsOrchestrator
from .prompt_submit_hooks import (
    PromptSubmitHookGenerator,
    resolve_prompt_submit_hook_agents,
)
from .wizard.models import Phase456RunResult


class Phase456Generator:
    """Orchestrate Phase 4-6: load governance  write source  compile  deploy  validate."""

    def __init__(
        self,
        repo_root: Path,
        output_base: Path,
        config: dict[str, Any],
        verbose: bool = False,
        selected_seedlings: set[str] | None = None,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        paths = get_sdd_paths()
        self.repo_root = repo_root or paths["root"]
        self.paths = paths
        self.output_base = output_base
        self.config = config
        self.verbose = verbose
        self.selected_seedlings = selected_seedlings
        self._emit = emitter or print

        self.dir = output_base / RUNTIME_DIRNAME
        self.source_dir = self.dir / "source"
        self.runtime_dir = self.dir / "runtime"
        self.mandates_dir = self.source_dir / "mandates"
        self.guidelines_dir = self.source_dir / "guidelines"
        self.governance_core_path, self.governance_client = _resolve_governance_inputs(
            self.repo_root, self.paths, output_base
        )

    def _write_sources(
        self,
        mandates: list[dict[str, Any]],
        guidelines: dict[str, dict[str, Any]],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        result: Phase456RunResult,
    ) -> bool:
        """Write source files (Phase 5)."""
        return write_phase5_sources(
            self.output_base,
            self.mandates_dir,
            self.guidelines_dir,
            self.source_dir,
            self.runtime_dir,
            mandates,
            guidelines,
            guidelines_by_category,
            self.config,
            self.verbose,
            result,
            _create_source_directories,
            _generate_plugin_workspace_dirs,
        )

    def _generate_seedlings(
        self,
        mandates: list[dict[str, Any]],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        result: Phase456RunResult,
    ) -> bool:
        """Generate intelligent seedlings."""
        seedlings = SeedlingsOrchestrator(
            output_base=self.output_base,
            mandates=mandates,
            guidelines_by_category=guidelines_by_category,
            config=self.config,
            governance_core_path=self.governance_core_path,
            paths=self.paths,
            verbose=self.verbose,
            emitter=self._emit,
        )
        if not seedlings.generate(selected=self.selected_seedlings):
            result["errors"].append("Failed to generate intelligent seedlings")
            return False
        return True

    def _generate_prompt_submit_hooks(self, result: Phase456RunResult) -> bool:
        """Generate runtime prompt-submit hooks when hook handshake mode is enabled."""
        if self.config.get("handshake_mode") != "hook":
            return True
        agents = resolve_prompt_submit_hook_agents(self.selected_seedlings)
        self.config["prompt_submit_hook_agents"] = sorted(agents)
        if not PromptSubmitHookGenerator(self.output_base, agents).generate():
            result["errors"].append(
                "handshake_mode=hook requires at least one supported hook agent "
                "(claude, codex, gemini)"
            )
            return False
        self._emit("hook...OK")
        return True

    def run(self) -> Phase456RunResult:
        """Execute Phase 4-6 generation."""
        return run_phase456_pipeline(self)


def run_phase_4_5_6_generator(
    repo_root: Path,
    output_base: Path,
    config: dict[str, Any],
    selected_seedlings: set[str] | None = None,
    debug: bool = False,
) -> Phase456RunResult:
    """Entry point for Phase 4-6 generator."""
    generator = Phase456Generator(
        repo_root,
        output_base,
        config,
        verbose=debug,
        selected_seedlings=selected_seedlings,
    )
    return generator.run()
