"""Tests for MandatesCompiler."""

from __future__ import annotations

from pathlib import Path

from providence_wizard.orchestration.wizard.mandates_compiler import MandatesCompiler


def _make_compiler(tmp_path: Path) -> MandatesCompiler:
    return MandatesCompiler(tmp_path, language="Python", emitter=lambda _: None)


def test_write_creates_mandates_md(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    mandates = [
        {
            "id": "M001",
            "title": "Bootstrap",
            "criticality": "MANDATORY",
            "description": "Desc.",
        }
    ]
    result = compiler.write(mandates)
    assert result is True
    out = tmp_path / "source" / "mandates" / "mandates.md"
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "M001" in content
    assert "Bootstrap" in content


def test_write_uses_summary_runtime_fallback(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    mandates = [
        {
            "id": "M003",
            "title": "Context Awareness",
            "criticality": "MANDATORY",
            "summary_runtime": "Maintain project-scoped task context.",
        }
    ]

    result = compiler.write(mandates)

    assert result is True
    content = (tmp_path / "source" / "mandates" / "mandates.md").read_text(
        encoding="utf-8"
    )
    assert "Maintain project-scoped task context." in content
    assert "No description available" not in content


def test_write_returns_false_on_error(tmp_path: Path) -> None:
    compiler = MandatesCompiler(
        tmp_path / "nonexistent" / "deep", emitter=lambda _: None
    )
    # Should still succeed (mkdir is called inside)
    result = compiler.write([])
    assert isinstance(result, bool)


def test_write_empty_mandates_creates_file(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    result = compiler.write([])
    assert result is True
    assert (tmp_path / "source" / "mandates" / "mandates.md").exists()
