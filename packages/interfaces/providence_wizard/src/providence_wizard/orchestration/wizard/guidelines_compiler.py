"""Guidelines source-file compiler for Phase 3 output."""

from __future__ import annotations

import traceback
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any


class GuidelinesCompiler:
    """Write AI-optimised per-category guidelines files."""

    def __init__(
        self,
        output_path: Path,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self._output_path = output_path
        self._emit = emitter or print

    def write(self, guidelines: list[dict[str, Any]]) -> bool:
        """Generate per-category .md files under output_path/source/guidelines/."""
        try:
            guidelines_dir = self._output_path / "source" / "guidelines"
            guidelines_dir.mkdir(parents=True, exist_ok=True)

            by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for guideline in guidelines:
                by_category[guideline.get("category", "general")].append(guideline)

            expected_files = {
                f"{category.lower().replace(' ', '-')}.md" for category in by_category
            }
            for existing in guidelines_dir.glob("*.md"):
                if existing.name not in expected_files:
                    existing.unlink()

            for category, items in sorted(by_category.items()):
                filename = category.lower().replace(" ", "-")
                lines = [
                    f"# {category.title()} Guidelines",
                    "",
                    " IA-FIRST DESIGN NOTICE",
                    "- **Status**: Customizable best practices",
                    "- **Optimization**: Optimized for AI agent parsing",
                    f"- **Category**: {category.title()}",
                    f"- **Count**: {len(items)} guidelines",
                    f"- **Generated**: {datetime.now().isoformat()}",
                    "",
                    "## Overview",
                    "",
                    f"Guidelines in this category provide structured recommendations for {category.lower()}.",
                    "",
                ]

                for guideline in items:
                    lines += [
                        f"## {guideline['id']}: {guideline['title']}",
                        "",
                        f"**Type**: {guideline.get('type', 'GUIDELINE')}",
                        f"**Status**: {guideline.get('status', 'required')}",
                        f"**Customizable**: {'Yes' if guideline.get('customizable', True) else 'No'}",
                        "",
                        guideline.get(
                            "description",
                            guideline.get("content", "No description available"),
                        ),
                        "",
                    ]

                (guidelines_dir / f"{filename}.md").write_text(
                    "\n".join(lines), encoding="utf-8"
                )

            return True
        except Exception as exc:
            self._emit(f"   Error generating guidelines files: {exc}")
            traceback.print_exc()
            return False
