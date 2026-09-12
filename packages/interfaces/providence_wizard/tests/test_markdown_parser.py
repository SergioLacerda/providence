"""Tests for MarkdownParser."""

from __future__ import annotations

from pathlib import Path

import pytest

from providence_wizard.orchestration.wizard.markdown_parser import MarkdownParser


@pytest.fixture
def parser() -> MarkdownParser:
    return MarkdownParser()


class TestParseStatus:
    def test_required_status(self, parser: MarkdownParser) -> None:
        content = "**Status:** `required: true`"
        assert parser.parse_status(content) == "required"

    def test_optional_status(self, parser: MarkdownParser) -> None:
        content = "**Status:** `optional: true`"
        assert parser.parse_status(content) == "optional"

    def test_custom_status(self, parser: MarkdownParser) -> None:
        content = "**Status:** `custom: false`"
        assert parser.parse_status(content) == "custom"

    def test_defaults_to_required_when_absent(self, parser: MarkdownParser) -> None:
        assert parser.parse_status("no status field here") == "required"


class TestParseItems:
    def test_returns_empty_when_path_missing(
        self, parser: MarkdownParser, tmp_path: Path
    ) -> None:
        result = parser.parse_items(tmp_path / "nonexistent")
        assert result["mandates"] == []
        assert result["guidelines"] == []

    def test_returns_empty_when_no_md_files(
        self, parser: MarkdownParser, tmp_path: Path
    ) -> None:
        tmp_path.mkdir(exist_ok=True)
        result = parser.parse_items(tmp_path)
        assert result["mandates"] == []
        assert result["guidelines"] == []

    def test_parses_mandate_items(self, parser: MarkdownParser, tmp_path: Path) -> None:
        (tmp_path / "mandates.md").write_text(
            "## M001: Test Mandate\n**Status:** `required: true`\nDescription.\n",
            encoding="utf-8",
        )
        result = parser.parse_items(tmp_path)
        assert len(result["mandates"]) == 1
        assert result["mandates"][0]["id"] == "M001"
        assert result["mandates"][0]["type"] == "HARD"

    def test_parses_guideline_items(
        self, parser: MarkdownParser, tmp_path: Path
    ) -> None:
        (tmp_path / "guidelines.md").write_text(
            "## G001: Test Guideline\n**Status:** `required: true`\nDesc.\n",
            encoding="utf-8",
        )
        result = parser.parse_items(tmp_path)
        assert len(result["guidelines"]) == 1
        assert result["guidelines"][0]["id"] == "G001"
        assert result["guidelines"][0]["type"] == "SOFT"

    def test_skips_optional_items(self, parser: MarkdownParser, tmp_path: Path) -> None:
        (tmp_path / "mixed.md").write_text(
            "## M001: Required\n**Status:** `required: true`\n\n"
            "## M002: Optional\n**Status:** `optional: true`\n",
            encoding="utf-8",
        )
        result = parser.parse_items(tmp_path)
        assert len(result["mandates"]) == 1
        assert result["mandates"][0]["id"] == "M001"
