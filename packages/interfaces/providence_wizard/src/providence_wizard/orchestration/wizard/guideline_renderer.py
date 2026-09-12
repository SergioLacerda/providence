"""Guideline markdown template renderer for Phase 1."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from providence_wizard.templates.guideline_templates import (
    guideline_block,
    guideline_category_header,
)

from .category_grouper import group_by_category


class GuidelineRenderer:
    """Write per-category guideline markdown files to an output directory."""

    def __init__(
        self,
        output_path: Path,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self._output_path = output_path
        self._emit = emitter or print

    def render(self, guidelines: list[Any]) -> bool:
        """Write guidelines-<category>.md files; return True on success."""
        if not guidelines:
            return True
        try:
            by_category = group_by_category(guidelines)
            for category, items in sorted(by_category.items()):
                filepath = self._output_path / f"guidelines-{category}.md"
                content = guideline_category_header(category)
                content += "".join(guideline_block(g) for g in items)
                filepath.write_text(content, encoding="utf-8")
            return True
        except Exception as exc:
            self._emit(f"   Error rendering guidelines: {exc}")
            return False
