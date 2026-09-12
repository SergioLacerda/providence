"""Tests for providence_pages.metadata."""

from __future__ import annotations

from pathlib import Path

import pytest

from providence_pages.metadata import MetadataExtractor

pytestmark = pytest.mark.unit


class TestExtractFromText:
    def test_extracts_full_frontmatter(self) -> None:
        text = (
            "---\n"
            "title: Hello World\n"
            "description: A test doc\n"
            "date: 2026-01-01\n"
            "tags: [a, b]\n"
            "author: Sergio\n"
            "---\n"
            "Body content here.\n"
        )
        metadata = MetadataExtractor().extract_from_text(text)
        assert metadata.title == "Hello World"
        assert metadata.description == "A test doc"
        assert metadata.date == "2026-01-01"
        assert metadata.tags == ["a", "b"]
        assert metadata.author == "Sergio"
        assert "Body content here." in metadata.body

    def test_no_frontmatter_returns_body_only(self) -> None:
        text = "# Just a heading\nNo frontmatter."
        metadata = MetadataExtractor().extract_from_text(text)
        assert metadata.title == ""
        assert metadata.body == text

    def test_malformed_yaml_returns_empty_metadata(self) -> None:
        text = "---\ntitle: [unclosed\n---\nBody\n"
        metadata = MetadataExtractor().extract_from_text(text)
        assert metadata.title == ""

    def test_non_dict_frontmatter_returns_empty_metadata(self) -> None:
        text = "---\n- a\n- b\n---\nBody\n"
        metadata = MetadataExtractor().extract_from_text(text)
        assert metadata.title == ""

    def test_single_tag_string_is_wrapped_in_list(self) -> None:
        text = "---\ntitle: X\ntags: solo\n---\nBody\n"
        metadata = MetadataExtractor().extract_from_text(text)
        assert metadata.tags == ["solo"]

    def test_missing_tags_field_defaults_to_empty_list(self) -> None:
        text = "---\ntitle: X\n---\nBody\n"
        metadata = MetadataExtractor().extract_from_text(text)
        assert metadata.tags == []

    def test_raw_contains_all_parsed_fields(self) -> None:
        text = "---\ntitle: X\ncustom_field: value\n---\nBody\n"
        metadata = MetadataExtractor().extract_from_text(text)
        assert metadata.raw["custom_field"] == "value"


class TestExtractFromFile:
    def test_extracts_from_file_on_disk(self, tmp_path: Path) -> None:
        file_path = tmp_path / "doc.md"
        file_path.write_text("---\ntitle: From File\n---\nContent\n", encoding="utf-8")
        metadata = MetadataExtractor().extract(file_path)
        assert metadata.title == "From File"
