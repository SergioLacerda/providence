"""Unit tests for providence_cli.services.lint_handler  legacy patterns and file collection."""

from __future__ import annotations

from pathlib import Path

import pytest

from providence_cli.services.lint_handler import (
    _check_legacy_patterns,
    _check_project_leaks,
    _collect_active_markdown_files,
    _collect_anchor_files,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _check_legacy_patterns
# ---------------------------------------------------------------------------


class TestCheckLegacyPatterns:
    def test_no_legacy_returns_0(self, tmp_path: Path) -> None:
        doc = tmp_path / "clean.md"
        doc.write_text("# Clean doc\n", encoding="utf-8")
        assert _check_legacy_patterns(tmp_path, tmp_path) == 0

    def test_legacy_docs_specs_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "stale.md"
        doc.write_text("See docs/specs/some-file.md\n", encoding="utf-8")
        assert _check_legacy_patterns(tmp_path, tmp_path) == 1

    def test_legacy_runtime_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "stale.md"
        doc.write_text("path is /runtime/something\n", encoding="utf-8")
        assert _check_legacy_patterns(tmp_path, tmp_path) == 1

    def test_legacy_reality_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "stale.md"
        doc.write_text("/REALITY/something\n", encoding="utf-8")
        assert _check_legacy_patterns(tmp_path, tmp_path) == 1

    def test_legacy_development_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "stale.md"
        doc.write_text("/DEVELOPMENT/foo\n", encoding="utf-8")
        assert _check_legacy_patterns(tmp_path, tmp_path) == 1

    def test_legacy_sdd_generated_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "stale.md"
        doc.write_text("see providence-generated/file\n", encoding="utf-8")
        assert _check_legacy_patterns(tmp_path, tmp_path) == 1


# ---------------------------------------------------------------------------
# _check_project_leaks
# ---------------------------------------------------------------------------


class TestCheckProjectLeaks:
    def test_no_leaks_returns_0(self, tmp_path: Path) -> None:
        core = tmp_path / "core"
        core.mkdir()
        (core / "doc.md").write_text("# Clean\n", encoding="utf-8")
        assert _check_project_leaks(tmp_path, tmp_path) == 0

    def test_rpg_narrative_leak_returns_1(self, tmp_path: Path) -> None:
        core = tmp_path / "core"
        core.mkdir()
        (core / "doc.md").write_text("rpg-narrative-server\n", encoding="utf-8")
        assert _check_project_leaks(tmp_path, tmp_path) == 1

    def test_game_master_leak_returns_1(self, tmp_path: Path) -> None:
        core = tmp_path / "core"
        core.mkdir()
        (core / "doc.md").write_text("game-master rules\n", encoding="utf-8")
        assert _check_project_leaks(tmp_path, tmp_path) == 1

    def test_no_core_dir_returns_0(self, tmp_path: Path) -> None:
        assert _check_project_leaks(tmp_path, tmp_path) == 0


# ---------------------------------------------------------------------------
# _collect_active_markdown_files
# ---------------------------------------------------------------------------


class TestCollectActiveMarkdownFiles:
    def test_collects_docs_markdown(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "guide.md").write_text("", encoding="utf-8")
        files = _collect_active_markdown_files(tmp_path)
        assert any(f.name == "guide.md" for f in files)

    def test_excludes_archive(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        archive = docs / "archive"
        archive.mkdir(parents=True)
        (archive / "old.md").write_text("", encoding="utf-8")
        (docs / "current.md").write_text("", encoding="utf-8")
        files = _collect_active_markdown_files(tmp_path)
        assert not any(f.name == "old.md" for f in files)
        assert any(f.name == "current.md" for f in files)

    def test_collects_readme(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("", encoding="utf-8")
        files = _collect_active_markdown_files(tmp_path)
        assert any(f.name == "README.md" for f in files)

    def test_collects_readme_detailed(self, tmp_path: Path) -> None:
        (tmp_path / "readme-detailed.md").write_text("", encoding="utf-8")
        files = _collect_active_markdown_files(tmp_path)
        assert any(f.name == "readme-detailed.md" for f in files)


# ---------------------------------------------------------------------------
# _collect_anchor_files
# ---------------------------------------------------------------------------


class TestCollectAnchorFiles:
    def test_validate_all_anchors_true(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "doc.md").write_text("", encoding="utf-8")
        files = _collect_anchor_files(tmp_path, validate_all_anchors=True)
        assert any(f.name == "doc.md" for f in files)

    def test_validate_all_false_wizard_dir_not_exists(self, tmp_path: Path) -> None:
        files = _collect_anchor_files(tmp_path, validate_all_anchors=False)
        assert files == []

    def test_validate_all_false_wizard_candidates(self, tmp_path: Path) -> None:
        wizard_dir = (
            tmp_path
            / "docs"
            / "spec"
            / "reality"
            / "implementation-analyses"
            / "wizard"
        )
        wizard_dir.mkdir(parents=True)
        start_here = wizard_dir / "START_HERE_FOR_DOCUMENTATION.md"
        start_here.write_text("", encoding="utf-8")
        files = _collect_anchor_files(tmp_path, validate_all_anchors=False)
        assert any(f.name == "START_HERE_FOR_DOCUMENTATION.md" for f in files)
