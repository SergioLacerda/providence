"""GeneratedManifest  tracks files written during a generation run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GeneratedManifest:
    """Record of files produced during wizard generation."""

    mandates_file: Path | None = None
    guideline_files: list[Path] = field(default_factory=list)
    source_readme: Path | None = None
    runtime_readme: Path | None = None
    extra_files: list[Path] = field(default_factory=list)

    @property
    def all_files(self) -> list[Path]:
        """Flat list of all files recorded in this manifest."""
        files: list[Path] = []
        if self.mandates_file:
            files.append(self.mandates_file)
        files.extend(self.guideline_files)
        if self.source_readme:
            files.append(self.source_readme)
        if self.runtime_readme:
            files.append(self.runtime_readme)
        files.extend(self.extra_files)
        return files
