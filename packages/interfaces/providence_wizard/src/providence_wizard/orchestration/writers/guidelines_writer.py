"""GuidelinesWriter  generates .providence/source/guidelines/<category>.md files."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from providence_core.utils.log import get_logger

logger = get_logger(__name__)

_CATEGORY_NAMES: dict[str, str] = {
    "architecture": "Architecture",
    "testing": "Testing",
    "git": "Git Workflow",
    "naming": "Naming Conventions",
    "docs": "Documentation",
    "style": "Code Style",
    "performance": "Performance",
    "security": "Security",
    "other": "Other Guidelines",
}


class GuidelinesWriter:
    """Write per-category guideline files to the guidelines output directory."""

    def __init__(
        self,
        guidelines_dir: Path,
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        verbose: bool = False,
    ) -> None:
        self._guidelines_dir = guidelines_dir
        self._guidelines_by_category = guidelines_by_category
        self._verbose = verbose

    def _log(self, message: str) -> None:
        if self._verbose:
            print(message)  # noqa: T201
        else:
            logger.debug(message)

    def generate(self) -> bool:
        """Write per-category .md files; return True on success."""
        self._log("Generating guidelines by category")
        try:
            for category, guidelines in self._guidelines_by_category.items():
                friendly_name = _CATEGORY_NAMES.get(category, category.title())
                guidelines_file = self._guidelines_dir / f"{category}.md"
                content = f"""# {friendly_name} Guidelines

 IA-FIRST DESIGN NOTICE
- **Status**: Customizable best practices
- **Optimization**: Optimized for AI agent parsing
- **Category**: {friendly_name}
- **Count**: {len(guidelines)} guidelines
- **Generated**: {datetime.now().isoformat()}

## Overview

Guidelines in this category provide structured recommendations for {friendly_name.lower()}.

"""
                for guideline in guidelines:
                    guideline_id = guideline.get("id", "G000")
                    guideline_title = (
                        guideline.get("title") or f"Guideline {guideline_id}"
                    )
                    content += f"""### {guideline_id}: {guideline_title}

**Type**: {guideline.get("type", "GUIDELINE")}
**Status**: {guideline.get("status", "required")}
**Customizable**: {"Yes" if guideline.get("customizable", True) else "No"}

{guideline.get("content", "No description available")}

"""
                with open(guidelines_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self._log(f"Generated {category}.md ({len(guidelines)} guidelines)")
            return True
        except Exception as e:
            print(f"   Failed to generate guidelines files: {e}")  # noqa: T201
            return False
