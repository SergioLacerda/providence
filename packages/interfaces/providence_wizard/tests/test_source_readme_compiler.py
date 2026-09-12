"""Tests for SourceReadmeCompiler."""

from __future__ import annotations

from pathlib import Path

from providence_wizard.orchestration.wizard.source_readme_compiler import (
    SourceReadmeCompiler,
)


def _make_compiler(tmp_path: Path) -> SourceReadmeCompiler:
    return SourceReadmeCompiler(tmp_path, language="Python", emitter=lambda _: None)


def test_write_creates_readme(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    result = compiler.write([], [])
    assert result is True
    assert (tmp_path / "source" / "README.md").exists()


def test_write_includes_mandate_count(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    mandates = [{"id": "M001", "title": "T"}]
    compiler.write(mandates, [])
    content = (tmp_path / "source" / "README.md").read_text(encoding="utf-8")
    assert "Count: 1" in content


def test_write_includes_categories(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    guidelines = [
        {"id": "G001", "title": "A", "category": "security"},
        {"id": "G002", "title": "B", "category": "testing"},
    ]
    compiler.write([], guidelines)
    content = (tmp_path / "source" / "README.md").read_text(encoding="utf-8")
    assert "Security" in content
    assert "Testing" in content
