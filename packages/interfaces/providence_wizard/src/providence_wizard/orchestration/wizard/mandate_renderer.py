"""Mandate markdown template renderer for Phase 1."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from providence_wizard.templates.mandate_templates import (
    mandate_block,
    mandate_category_header,
)

from .category_grouper import group_by_category


class MandateRenderer:
    """Write per-category mandate markdown files to an output directory."""

    def __init__(
        self,
        output_path: Path,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self._output_path = output_path
        self._emit = emitter or print

    def render(self, mandates: list[Any]) -> bool:
        """Write mandates-<category>.md files; return True on success."""
        if not mandates:
            return True
        try:
            by_category = group_by_category(mandates)
            for category, items in sorted(by_category.items()):
                filepath = self._output_path / f"mandates-{category}.md"
                content = mandate_category_header(category)
                content += "".join(mandate_block(m) for m in items)
                filepath.write_text(content, encoding="utf-8")
            return True
        except Exception as exc:
            self._emit(f"   Error rendering mandates: {exc}")
            return False
