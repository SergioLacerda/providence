"""Phase 3 Compiler  orchestrates template compilation pipeline."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from providence_wizard.constants import (
    GOVERNANCE_CLIENT_FILENAME as _GOVERNANCE_CLIENT_FILENAME,
)
from providence_wizard.constants import (
    GOVERNANCE_CORE_FILENAME as _GOVERNANCE_CORE_FILENAME,
)
from providence_wizard.constants import PHASE2_INPUT_DIRNAME as _PHASE2_INPUT_DIRNAME
from providence_wizard.constants import (
    WIZARD_CONFIG_FILENAME as _WIZARD_CONFIG_FILENAME,
)

from ._phase3_helpers import (
    _compile_with_pipeline_builder,
    _copy_seedlings,
    _generate_source_files,
    _generate_spec_file,
    _load_compiled_governance,
)
from .markdown_parser import MarkdownParser
from .models import ParsedItems, Phase3RunResult
from .template_locator import TemplateLocator


class Phase3Compiler:
    """Compile edited markdown templates to governance artifacts."""

    PHASE2_INPUT_DIRNAME = _PHASE2_INPUT_DIRNAME
    WIZARD_CONFIG_FILENAME = _WIZARD_CONFIG_FILENAME

    def __init__(
        self,
        markdown_input_path: Path,
        output_path: Path,
        repo_root: Path,
        verbose: bool = False,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self.markdown_input_path = markdown_input_path
        self.output_path = output_path
        self.repo_root = repo_root
        self.verbose = verbose
        self.language = "Python"
        self.config: dict[str, Any] = {}
        self.selected_guidelines: list[str] = []
        self.client_build_dir = self.markdown_input_path.parent
        self.phase2_input_dir = self.client_build_dir / self.PHASE2_INPUT_DIRNAME
        self.wizard_config_path = self.client_build_dir / self.WIZARD_CONFIG_FILENAME
        self._emit = emitter or print
        self._parser = MarkdownParser()
        self._locator = TemplateLocator(repo_root, self._emit)

    @property
    def last_error(self) -> str | None:
        """Last error message from the template locator."""
        return self._locator.last_error

    @last_error.setter
    def last_error(self, value: str | None) -> None:
        self._locator.last_error = value

    def log(self, message: str) -> None:
        """Emit a verbose-only info message."""
        if self.verbose:
            self._emit(f"    {message}")

    def validate_template_root(self) -> bool:
        """Return True if the wizard templates directory exists under repo_root."""
        return self._locator.validate_template_root()

    def resolve_language_template_dir(self) -> Path | None:
        """Return the language-specific template directory, or None if missing."""
        return self._locator.resolve_language_dir(self.language)

    def has_staged_input_files(self) -> bool:
        """Return True if any markdown files exist in markdown_input_path."""
        if not self.markdown_input_path.exists():
            return False
        return any(path.is_file() for path in self.markdown_input_path.iterdir())

    def load_wizard_config(self) -> bool:
        """Load wizard.json config from the client build directory."""
        try:
            if self.wizard_config_path.exists():
                with open(self.wizard_config_path, encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.language = self.config.get("language", "Python")
            return True
        except Exception as exc:
            self._emit(f"   Error loading config: {exc}")
            return False

    def create_structure(self) -> bool:
        """Create .providence/source/ directory tree."""
        try:
            (self.output_path / "source").mkdir(parents=True, exist_ok=True)
            return True
        except Exception as exc:
            self._emit(f"   Error creating structure: {exc}")
            return False

    def copy_seedlings(self) -> bool:
        """Copy pre-built seedling JSON files into the output .providence/seedlings/ directory."""
        return _copy_seedlings(self.repo_root, self.output_path, self._emit)

    def parse_markdown_items(self) -> ParsedItems:
        """Parse staged markdown templates into mandate/guideline dicts."""
        items = self._parser.parse_items(self.markdown_input_path)
        self.selected_guidelines = [g["id"] for g in items["guidelines"]]
        return items

    def compile_with_pipeline_builder(self, items: ParsedItems) -> bool:
        """Run PipelineBuilder on parsed items and save outputs to .providence/source/."""
        return _compile_with_pipeline_builder(
            self.repo_root, self.output_path, cast(dict[str, Any], items), self._emit
        )

    def load_compiled_governance(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Load compiled mandates and guidelines from .providence/source/."""
        return _load_compiled_governance(self.output_path, self._emit)

    def run(self) -> Phase3RunResult:
        """Execute all Phase 3 steps and return a result dict."""
        self._emit("phase3...OK")

        if not self.has_staged_input_files():
            return {
                "success": False,
                "error": (
                    f"No staged files found in {self.markdown_input_path}. "
                    "Run Phase 2 after editing templates to populate phase-2-input."
                ),
            }

        if not self.load_wizard_config():
            return {"success": False, "error": "Failed to load config"}
        if not self.create_structure():
            return {"success": False, "error": "Failed to create .providence structure"}

        items = self.parse_markdown_items()
        self._emit(f"parse...OK ({len(items['mandates'])} mandates)")
        self._emit(f"guidelines...OK ({len(items['guidelines'])})")

        if not self.compile_with_pipeline_builder(items):
            return {"success": False, "error": "Failed to compile"}

        spec_emitter = self._emit if self.verbose else (lambda _message: None)
        _generate_spec_file(self.repo_root, self.output_path, spec_emitter)

        if not self.copy_seedlings():
            return {"success": False, "error": "Failed to copy seedlings"}

        mandates, guidelines = self.load_compiled_governance()
        if mandates or guidelines:
            err = _generate_source_files(
                self.output_path, self.language, self._emit, mandates, guidelines
            )
            if err:
                return {"success": False, "error": err}

        self._emit("compile...OK")
        self._emit(f"output...OK {self.output_path}")

        return {
            "success": True,
            "output_path": str(self.output_path),
            "language": self.language,
            "files": [
                _GOVERNANCE_CORE_FILENAME,
                _GOVERNANCE_CLIENT_FILENAME,
                "seedling/",
                "mandates.md",
                "guidelines/",
            ],
            "mandates": len(mandates),
            "guidelines": len(guidelines),
        }
