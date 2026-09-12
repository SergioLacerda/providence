"""Phase 1 Generator  orchestrates governance template generation."""

from __future__ import annotations

import importlib.resources
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from providence_core.utils.environment import get_sdd_paths
from providence_wizard.constants import PHASE2_INPUT_DIRNAME as _PHASE2_INPUT_DIRNAME

from ._phase1_helpers import (
    apply_selector_selection,
    candidate_names,
    selector_selection_ids,
    write_markdown_templates,
)
from .models import Guideline, Mandate, Phase1RunResult
from .spec_parser import GuidelinesDslParser, MandateSpecParser


def _bundled_spec_dir() -> Path | None:
    """Resolve the directory containing providence_core's packaged canonical mandate.spec/guidelines.dsl."""
    try:
        pkg_dir = importlib.resources.files("providence_core")
    except (ImportError, ModuleNotFoundError):
        return None
    candidate = Path(str(pkg_dir))
    return candidate if candidate.is_dir() else None


@dataclass
class Phase1Generator:
    """Generate markdown templates from governance source files."""

    PHASE2_INPUT_DIRNAME = _PHASE2_INPUT_DIRNAME

    def __init__(
        self,
        core_path: Path,
        output_path: Path,
        verbose: bool = False,
        config: dict[str, Any] | None = None,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self.core_path = core_path
        self.output_path = output_path
        self.verbose = verbose
        self.config = config or {}
        self.language = self.config.get("language", "Python")
        self.adoption_level = self.config.get("adoption_level", "FULL")
        self.mandates: list[Mandate] = []
        self.guidelines: list[Guideline] = []
        self.last_error: str | None = None
        self.resolved_source_files: dict[str, Path] = {}
        self.local_source_dir = self.output_path.parent
        self.source_spec_dirs: list[Path] = []
        self._emit = emitter or print
        self._mandate_parser = MandateSpecParser(emitter)
        self._guideline_parser = GuidelinesDslParser(emitter)
        self._init_source_dirs()

    def _init_source_dirs(self) -> None:
        candidates: list[Path] = []
        bundled = _bundled_spec_dir()
        if bundled is not None:
            candidates.append(bundled)
        try:
            paths = get_sdd_paths()
            docs_meta_dir = paths.get("docs_meta", self.local_source_dir / "docs-meta")
            source_spec_dir = paths.get("source_spec", docs_meta_dir)
            candidates.extend(
                [
                    source_spec_dir,
                    self.local_source_dir / "docs-meta",
                    docs_meta_dir,
                ]
            )
        except RuntimeError:
            candidates.append(self.local_source_dir / "docs-meta")
        self.source_spec_dirs = list(dict.fromkeys(candidates))

    def log(self, message: str) -> None:
        """Emit a verbose-only info message."""
        if self.verbose:
            self._emit(f"    {message}")

    def _resolve_source_file(self, filename: str) -> Path | None:
        candidates = [
            source_dir / name
            for source_dir in self.source_spec_dirs
            for name in candidate_names(filename)
        ]
        for candidate in candidates:
            if candidate.exists():
                self.resolved_source_files[filename] = candidate
                return candidate
        self.last_error = (
            f"{filename} not found. Searched: {', '.join(str(p) for p in candidates)}. "
            "Run 'providence governance compile' to regenerate governance artifacts."
        )
        self._emit(f"   {self.last_error}")
        return None

    def parse_mandate_spec(self) -> bool:
        """Parse mandate.spec (or mandate.md) and populate self.mandates."""
        path = self._resolve_source_file("mandate.spec")
        if path is None:
            return False
        content = path.read_text(encoding="utf-8")
        self.mandates = self._mandate_parser.parse(
            content, is_markdown=path.suffix == ".md"
        )
        return len(self.mandates) > 0

    def parse_guidelines_dsl(self) -> bool:
        """Parse guidelines.dsl (or guidelines.md) and populate self.guidelines."""
        path = self._resolve_source_file("guidelines.dsl")
        if path is None:
            return False
        content = path.read_text(encoding="utf-8")
        self.guidelines = self._guideline_parser.parse(
            content, is_markdown=path.suffix == ".md"
        )
        return True

    def _apply_selector_selection(self) -> bool:
        selected_ids = selector_selection_ids(self.config)
        mandates, guidelines, error = apply_selector_selection(
            self.mandates, self.guidelines, selected_ids
        )
        if error:
            self.last_error = error
            self._emit(f"   {self.last_error}")
            return False
        self.mandates = mandates
        self.guidelines = guidelines
        return True

    def generate_markdown_templates(self) -> bool:
        """Write per-category mandate and guideline markdown files to output_path."""
        write_markdown_templates(
            self.output_path,
            self.mandates,
            self.guidelines,
            self.language,
            self.adoption_level,
            self._emit,
        )
        return True

    def run(self) -> Phase1RunResult:
        """Execute all Phase 1 steps and return a result dict."""
        self._emit("phase1...OK")

        mandate_file = self._resolve_source_file("mandate.spec")
        if mandate_file is None:
            return {
                "success": False,
                "error": self.last_error or "Failed to locate mandate.spec",
            }

        guidelines_file = self._resolve_source_file("guidelines.dsl")
        if guidelines_file is None:
            return {
                "success": False,
                "error": self.last_error or "Failed to locate guidelines.dsl",
            }

        if not self.parse_mandate_spec():
            return {
                "success": False,
                "error": self.last_error or "Failed to parse mandate.spec",
            }

        if not self.parse_guidelines_dsl():
            return {
                "success": False,
                "error": self.last_error or "Failed to parse guidelines.dsl",
            }

        if not self._apply_selector_selection():
            return {
                "success": False,
                "error": self.last_error or "Failed to apply selector selection",
            }

        if not self.generate_markdown_templates():
            return {"success": False, "error": "Failed to generate markdown templates"}

        (self.output_path.parent / self.PHASE2_INPUT_DIRNAME).mkdir(
            parents=True, exist_ok=True
        )

        self._emit(f"mandates...OK ({len(self.mandates)})")
        self._emit(f"guidelines...OK ({len(self.guidelines)})")

        return {
            "success": True,
            "mandate_count": len(self.mandates),
            "guideline_count": len(self.guidelines),
            "mandate_spec_output": str(mandate_file),
            "output_path": str(self.output_path),
            "mandates": [m.to_dict() for m in self.mandates],
            "guidelines": [g.to_dict() for g in self.guidelines],
        }
