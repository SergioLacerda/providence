"""Tests for providence_pages.delta."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from providence_pages.delta import DeltaIndexer
from providence_pages.selector import DocumentEntry

pytestmark = pytest.mark.unit


def _make_docs(tmp_path: Path, files: dict[str, str]) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    for name, content in files.items():
        target = docs / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return docs


class TestChangedFiles:
    def test_returns_empty_when_git_not_available(self, tmp_path: Path) -> None:
        docs = _make_docs(tmp_path, {"a.md": "# A"})
        with patch(
            "providence_pages.delta.SafeProcessRunner.run",
            side_effect=Exception("git not found"),
        ):
            result = DeltaIndexer().changed_files(docs)
        assert result == []

    def test_returns_empty_when_git_fails(self, tmp_path: Path) -> None:
        docs = _make_docs(tmp_path, {"a.md": "# A"})
        with patch("providence_pages.delta.SafeProcessRunner.run") as mock_run:
            mock_run.return_value = MagicMock(success=False, stdout="")
            result = DeltaIndexer().changed_files(docs)
        assert result == []


class TestIncrementalIndex:
    def test_returns_existing_when_no_changes(self, tmp_path: Path) -> None:
        existing = [DocumentEntry(path="a.md", title="A", url="/a.md")]
        docs = _make_docs(tmp_path, {"a.md": "# A"})
        with patch.object(DeltaIndexer, "changed_files", return_value=[]):
            result = DeltaIndexer().incremental_index(docs, existing)
        assert result == existing

    def test_adds_new_file_when_changed(self, tmp_path: Path) -> None:
        docs = _make_docs(tmp_path, {"a.md": "# A", "b.md": "# B"})
        existing = [DocumentEntry(path="a.md", title="A", url="/a.md")]
        b_path = docs / "b.md"
        with patch.object(DeltaIndexer, "changed_files", return_value=[b_path]):
            result = DeltaIndexer().incremental_index(docs, existing)
        paths = {e.path for e in result}
        assert "a.md" in paths
        assert "b.md" in paths


class TestCachedIndex:
    def test_reindexes_when_cache_empty(self, tmp_path: Path) -> None:
        docs = _make_docs(tmp_path, {"a.md": "---\ntitle: A\n---\nBody"})
        output = tmp_path / "index.json"
        cache = tmp_path / "cache.json"

        entries, was_cached = DeltaIndexer().cached_index(docs, output, cache)

        assert was_cached is False
        assert len(entries) == 1
        assert cache.exists()

    def test_uses_cache_when_no_changes(self, tmp_path: Path) -> None:
        docs = _make_docs(tmp_path, {"a.md": "---\ntitle: A\n---\nBody"})
        output = tmp_path / "index.json"
        cache = tmp_path / "cache.json"
        indexer = DeltaIndexer()

        entries, _ = indexer.cached_index(docs, output, cache)
        indexer._indexer.to_json(entries, output)

        entries2, was_cached = indexer.cached_index(docs, output, cache)
        assert was_cached is True
        assert len(entries2) == len(entries)

    def test_reindexes_when_file_content_changes(self, tmp_path: Path) -> None:
        docs = _make_docs(tmp_path, {"a.md": "---\ntitle: A\n---\nBody"})
        output = tmp_path / "index.json"
        cache = tmp_path / "cache.json"
        indexer = DeltaIndexer()

        entries, _ = indexer.cached_index(docs, output, cache)
        indexer._indexer.to_json(entries, output)

        (docs / "a.md").write_text(
            "---\ntitle: A Modified\n---\nNew body", encoding="utf-8"
        )

        entries2, was_cached = indexer.cached_index(docs, output, cache)
        assert was_cached is False
        assert entries2[0].title == "A Modified"
