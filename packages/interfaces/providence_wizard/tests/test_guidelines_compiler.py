"""Tests for GuidelinesCompiler."""

from __future__ import annotations

from pathlib import Path

from providence_wizard.orchestration.wizard.guidelines_compiler import (
    GuidelinesCompiler,
)


def _make_compiler(tmp_path: Path) -> GuidelinesCompiler:
    return GuidelinesCompiler(tmp_path, emitter=lambda _: None)


def test_write_creates_category_file(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    guidelines = [
        {
            "id": "G001",
            "title": "Code Style",
            "category": "testing",
            "description": "Desc.",
        }
    ]
    result = compiler.write(guidelines)
    assert result is True
    out = tmp_path / "source" / "guidelines" / "testing.md"
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "G001" in content
    assert "Code Style" in content


def test_write_groups_by_category(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    guidelines = [
        {"id": "G001", "title": "A", "category": "alpha", "description": ""},
        {"id": "G002", "title": "B", "category": "beta", "description": ""},
    ]
    result = compiler.write(guidelines)
    assert result is True
    assert (tmp_path / "source" / "guidelines" / "alpha.md").exists()
    assert (tmp_path / "source" / "guidelines" / "beta.md").exists()


def test_write_uses_general_category_when_missing(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    guidelines = [{"id": "G001", "title": "X", "description": ""}]
    result = compiler.write(guidelines)
    assert result is True
    assert (tmp_path / "source" / "guidelines" / "general.md").exists()


def test_write_removes_stale_category_files(tmp_path: Path) -> None:
    guidelines_dir = tmp_path / "source" / "guidelines"
    guidelines_dir.mkdir(parents=True)
    stale_file = guidelines_dir / "other.md"
    stale_file.write_text("stale", encoding="utf-8")

    result = _make_compiler(tmp_path).write(
        [{"id": "G001", "title": "X", "description": ""}]
    )

    assert result is True
    assert (guidelines_dir / "general.md").exists()
    assert not stale_file.exists()


def test_write_empty_guidelines_returns_true(tmp_path: Path) -> None:
    result = _make_compiler(tmp_path).write([])
    assert result is True
