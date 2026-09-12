"""Markdown parser for Phase 3 governance template compilation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import ParsedItems


class MarkdownParser:
    """Parse edited markdown files from phase-2-input into structured items."""

    _STATUS_PATTERN = re.compile(
        r"\*\*Status:\*\*\s*`(required|optional|custom):\s*(?:true|false)`"
    )
    _ITEM_PATTERN = re.compile(r"## ([GM]\d+):\s*(.+?)\n(.*?)(?=##|$)", re.DOTALL)

    def parse_status(self, content: str) -> str:
        """Extract status from markdown content; defaults to 'required'."""
        match = self._STATUS_PATTERN.search(content)
        return match.group(1) if match else "required"

    def parse_items(self, md_input_path: Path) -> ParsedItems:
        """Parse all .md files in md_input_path; skip optional items."""
        mandates: list[dict[str, Any]] = []
        guidelines: list[dict[str, Any]] = []

        if not md_input_path.exists():
            return ParsedItems(mandates=[], guidelines=[])

        md_files = list(md_input_path.glob("*.md"))
        if not md_files:
            return ParsedItems(mandates=[], guidelines=[])

        for md_file in md_files:
            content = md_file.read_text(encoding="utf-8")
            for match in self._ITEM_PATTERN.finditer(content):
                item_id = match.group(1)
                title = match.group(2).strip()
                item_content = match.group(3)
                status = self.parse_status(item_content)

                if status == "optional":
                    continue

                item: dict[str, Any] = {
                    "id": item_id,
                    "title": title,
                    "status": status,
                    "type": "HARD" if item_id.startswith("M") else "SOFT",
                }

                if item_id.startswith("M"):
                    mandates.append(item)
                else:
                    guidelines.append(item)

        return ParsedItems(mandates=mandates, guidelines=guidelines)
