"""Tests for providence_pages.validator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_pages.selector import INDEX_SCHEMA_VERSION
from providence_pages.validator import IndexValidator

pytestmark = pytest.mark.unit


def _write_index(path: Path, data: object) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


class TestIndexValidatorMissingFile:
    def test_returns_invalid_when_file_missing(self, tmp_path: Path) -> None:
        result = IndexValidator().validate(tmp_path / "missing.json")
        assert result.valid is False
        assert any("not found" in e for e in result.errors)


class TestIndexValidatorMalformedJson:
    def test_returns_invalid_for_bad_json(self, tmp_path: Path) -> None:
        p = tmp_path / "index.json"
        p.write_text("{not valid json", encoding="utf-8")
        result = IndexValidator().validate(p)
        assert result.valid is False
        assert any("Invalid JSON" in e for e in result.errors)

    def test_returns_invalid_when_root_not_object(self, tmp_path: Path) -> None:
        p = tmp_path / "index.json"
        _write_index(p, [1, 2, 3])
        result = IndexValidator().validate(p)
        assert result.valid is False


class TestIndexValidatorSchemaVersion:
    def test_warns_when_schema_version_differs(self, tmp_path: Path) -> None:
        p = tmp_path / "index.json"
        _write_index(
            p,
            {
                "schema_version": "0.9",
                "documents": [{"path": "a.md", "title": "A", "url": "/a.md"}],
            },
        )
        result = IndexValidator().validate(p)
        assert result.valid is True
        assert any("schema_version" in w for w in result.warnings)

    def test_no_warning_when_schema_version_matches(self, tmp_path: Path) -> None:
        p = tmp_path / "index.json"
        _write_index(
            p,
            {
                "schema_version": INDEX_SCHEMA_VERSION,
                "documents": [{"path": "a.md", "title": "A", "url": "/a.md"}],
            },
        )
        result = IndexValidator().validate(p)
        assert result.valid is True
        assert not any("schema_version" in w for w in result.warnings)


class TestIndexValidatorDocuments:
    def test_returns_invalid_when_documents_missing(self, tmp_path: Path) -> None:
        p = tmp_path / "index.json"
        _write_index(p, {"schema_version": INDEX_SCHEMA_VERSION})
        result = IndexValidator().validate(p)
        assert result.valid is False
        assert any("documents" in e for e in result.errors)

    def test_returns_invalid_for_entry_missing_required_field(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "index.json"
        _write_index(
            p,
            {
                "schema_version": INDEX_SCHEMA_VERSION,
                "documents": [{"path": "a.md", "url": "/a.md"}],
            },
        )
        result = IndexValidator().validate(p)
        assert result.valid is False
        assert any("title" in e for e in result.errors)

    def test_valid_index(self, tmp_path: Path) -> None:
        p = tmp_path / "index.json"
        _write_index(
            p,
            {
                "schema_version": INDEX_SCHEMA_VERSION,
                "documents": [{"path": "a.md", "title": "A", "url": "/a.md"}],
            },
        )
        result = IndexValidator().validate(p)
        assert result.valid is True
        assert result.errors == []


class TestIndexValidatorSourceDir:
    def test_warns_when_path_not_on_disk(self, tmp_path: Path) -> None:
        p = tmp_path / "index.json"
        source = tmp_path / "docs"
        source.mkdir()
        _write_index(
            p,
            {
                "schema_version": INDEX_SCHEMA_VERSION,
                "documents": [
                    {"path": "missing.md", "title": "X", "url": "/missing.md"}
                ],
            },
        )
        result = IndexValidator().validate(p, source_dir=source)
        assert result.valid is True
        assert any("not found" in w for w in result.warnings)

    def test_no_warning_when_path_exists(self, tmp_path: Path) -> None:
        source = tmp_path / "docs"
        source.mkdir()
        (source / "a.md").write_text("# A\n", encoding="utf-8")
        p = tmp_path / "index.json"
        _write_index(
            p,
            {
                "schema_version": INDEX_SCHEMA_VERSION,
                "documents": [{"path": "a.md", "title": "A", "url": "/a.md"}],
            },
        )
        result = IndexValidator().validate(p, source_dir=source)
        assert result.valid is True
        assert result.warnings == []
