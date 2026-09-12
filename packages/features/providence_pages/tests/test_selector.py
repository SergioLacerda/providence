"""Tests for providence_pages.selector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_pages.selector import (
    INDEX_SCHEMA_VERSION,
    DocumentEntry,
    DocumentIndexer,
    SelectorGenerator,
)

pytestmark = pytest.mark.unit


class TestSelectorGenerator:
    def test_generates_id_from_simple_path(self) -> None:
        entry = DocumentEntry(path="guide.md", title="Guide", url="/guide.md")
        selector = SelectorGenerator().generate(entry)
        assert selector == "doc-guide-md"

    def test_generates_id_from_nested_path(self) -> None:
        entry = DocumentEntry(
            path="docs/getting-started.md",
            title="Start",
            url="/docs/getting-started.md",
        )
        selector = SelectorGenerator().generate(entry)
        assert selector == "doc-docs-getting-started-md"

    def test_generates_fallback_id_for_empty_path(self) -> None:
        entry = DocumentEntry(path="", title="Root", url="/")
        selector = SelectorGenerator().generate(entry)
        assert selector == "doc-root"

    def test_strips_unsafe_characters(self) -> None:
        entry = DocumentEntry(
            path="docs/My File!.md", title="X", url="/docs/My File!.md"
        )
        selector = SelectorGenerator().generate(entry)
        assert " " not in selector
        assert "!" not in selector


class TestDocumentIndexer:
    def test_indexes_markdown_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text(
            "---\ntitle: A Doc\ntags: [x]\n---\nBody\n", encoding="utf-8"
        )
        (tmp_path / "b.md").write_text("No frontmatter", encoding="utf-8")

        entries = DocumentIndexer().index(tmp_path)

        assert len(entries) == 2
        by_path = {e.path: e for e in entries}
        assert by_path["a.md"].title == "A Doc"
        assert by_path["a.md"].tags == ["x"]
        assert by_path["b.md"].title == "b"

    def test_indexes_nested_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "docs"
        nested.mkdir()
        (nested / "nested.md").write_text("---\ntitle: Nested\n---\n", encoding="utf-8")

        entries = DocumentIndexer().index(tmp_path)

        assert len(entries) == 1
        assert entries[0].path == "docs/nested.md"
        assert entries[0].url == "/docs/nested.md"

    def test_ignores_non_matching_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("---\ntitle: A\n---\n", encoding="utf-8")
        (tmp_path / "ignored.txt").write_text("ignored", encoding="utf-8")

        entries = DocumentIndexer().index(tmp_path)

        assert len(entries) == 1
        assert entries[0].path == "a.md"

    def test_empty_directory_yields_no_entries(self, tmp_path: Path) -> None:
        entries = DocumentIndexer().index(tmp_path)
        assert entries == []

    def test_to_json_writes_expected_structure(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("---\ntitle: A\n---\n", encoding="utf-8")
        indexer = DocumentIndexer()
        entries = indexer.index(tmp_path)

        output_path = tmp_path / "index.json"
        indexer.to_json(entries, output_path)

        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert len(data["documents"]) == 1
        assert data["documents"][0]["path"] == "a.md"
        assert data["schema_version"] == INDEX_SCHEMA_VERSION
        assert "generated_at" in data

    def test_to_json_creates_parent_directories(self, tmp_path: Path) -> None:
        indexer = DocumentIndexer()
        output_path = tmp_path / "build" / "site" / "selector" / "docs.index.json"

        indexer.to_json([], output_path)

        assert output_path.exists()

    def test_to_search_json_includes_body(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text(
            "---\ntitle: A\n---\nThis is the body.\n", encoding="utf-8"
        )
        indexer = DocumentIndexer()
        entries = indexer.index(tmp_path)
        output_path = tmp_path / "search.index.json"
        indexer.to_search_json(entries, tmp_path, output_path)

        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["documents"][0]["body"].strip() == "This is the body."

    def test_to_search_json_creates_parent_directories(self, tmp_path: Path) -> None:
        indexer = DocumentIndexer()
        output_path = tmp_path / "build" / "site" / "selector" / "search.index.json"

        indexer.to_search_json([], tmp_path, output_path)

        assert output_path.exists()

    def test_indexes_date_and_category_from_frontmatter(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text(
            "---\ntitle: A\ndate: 2024-01-15\ncategory: guides\n---\nBody\n",
            encoding="utf-8",
        )
        entries = DocumentIndexer().index(tmp_path)
        assert entries[0].date == "2024-01-15"
        assert entries[0].category == "guides"

    def test_date_and_category_default_to_empty_string_when_absent(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "a.md").write_text("---\ntitle: A\n---\n", encoding="utf-8")
        entries = DocumentIndexer().index(tmp_path)
        assert entries[0].date == ""
        assert entries[0].category == ""

    def test_to_json_includes_date_and_category_fields(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text(
            "---\ntitle: A\ndate: 2024-03-01\ncategory: ref\n---\n", encoding="utf-8"
        )
        indexer = DocumentIndexer()
        entries = indexer.index(tmp_path)
        output_path = tmp_path / "docs.index.json"
        indexer.to_json(entries, output_path)

        data = json.loads(output_path.read_text(encoding="utf-8"))
        doc = data["documents"][0]
        assert doc["date"] == "2024-03-01"
        assert doc["category"] == "ref"


class TestSelectorTemplate:
    """Structural assertions on the packaged selector.js template."""

    def _template_path(self) -> Path:
        from importlib import resources

        asset_root = (
            resources.files("providence_wizard")
            .joinpath("templates")
            .joinpath("selector")
        )
        return Path(str(asset_root)) / "selector.js"

    def test_template_fetches_docs_index_json(self) -> None:
        content = self._template_path().read_text(encoding="utf-8")
        assert 'fetch("docs.index.json")' in content

    def test_template_fetch_failure_is_non_fatal(self) -> None:
        content = self._template_path().read_text(encoding="utf-8")
        assert "loadDocsIndex" in content
        assert "docsLoaded" in content

    def test_template_still_fetches_data_json_for_governance_items(self) -> None:
        content = self._template_path().read_text(encoding="utf-8")
        assert 'fetch("data.json")' in content
