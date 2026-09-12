"""Unit tests for tools.guardrails.checkers.doc_reference_checker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_core.utils.text_io import write_text_utf8
from tools.guardrails.checkers.doc_reference_checker import (
    DocReferenceChecker,
    _doc_references_detector,
    find_code_references,
)
from tools.guardrails.core.config import AnalysisConfig
from tools.guardrails.core.metrics import FileMetrics

pytestmark = pytest.mark.unit


class TestFindCodeReferences:
    """find_code_references extracts backtick-quoted docs/-consumer paths."""

    def test_finds_valid_reference(self, tmp_path: Path) -> None:
        (tmp_path / "packages" / "core").mkdir(parents=True)
        write_text_utf8(tmp_path / "packages" / "core" / "foo.py", "x = 1\n")

        content = "See `packages/core/foo.py` for details."
        refs = find_code_references(content, tmp_path)

        assert len(refs) == 1
        assert refs[0].resolved_path == "packages/core/foo.py"
        assert refs[0].exists is True

    def test_finds_broken_reference(self, tmp_path: Path) -> None:
        content = "See `packages/core/missing.py` for details."
        refs = find_code_references(content, tmp_path)

        assert len(refs) == 1
        assert refs[0].exists is False

    def test_strips_line_suffix_before_checking(self, tmp_path: Path) -> None:
        (tmp_path / "tools" / "sdd-compile" / "cmd").mkdir(parents=True)
        write_text_utf8(
            tmp_path / "tools" / "sdd-compile" / "cmd" / "main.go", "package main\n"
        )

        content = "Defined at `tools/sdd-compile/cmd/main.go:42`."
        refs = find_code_references(content, tmp_path)

        assert len(refs) == 1
        assert refs[0].resolved_path == "tools/sdd-compile/cmd/main.go"
        assert refs[0].text == "tools/sdd-compile/cmd/main.go:42"
        assert refs[0].exists is True

    def test_strips_line_range_suffix(self, tmp_path: Path) -> None:
        (tmp_path / "packages" / "core").mkdir(parents=True)
        write_text_utf8(tmp_path / "packages" / "core" / "Makefile-like.py", "x = 1\n")

        content = "See `packages/core/Makefile-like.py:10-20`."
        refs = find_code_references(content, tmp_path)

        assert refs[0].resolved_path == "packages/core/Makefile-like.py"
        assert refs[0].exists is True

    def test_ignores_bare_prose_mention_without_backticks(self, tmp_path: Path) -> None:
        content = "See the packages/core/missing.py directory for details."
        refs = find_code_references(content, tmp_path)

        assert refs == []

    def test_ignores_unrelated_backtick_paths(self, tmp_path: Path) -> None:
        content = "See `docs/README.md` or `packages/interfaces/providence_cli/cli.py`."
        refs = find_code_references(content, tmp_path)

        assert refs == []

    def test_line_number_is_1_based(self, tmp_path: Path) -> None:
        content = "line one\nline two\nrefers to `packages/core/missing.py` here\n"
        refs = find_code_references(content, tmp_path)

        assert refs[0].line == 3

    def test_multiple_references_in_document_order(self, tmp_path: Path) -> None:
        content = "First `packages/core/a.py`.\nThen `tools/sdd-compile/b.go`.\n"
        refs = find_code_references(content, tmp_path)

        assert [r.resolved_path for r in refs] == [
            "packages/core/a.py",
            "tools/sdd-compile/b.go",
        ]


class TestDocReferencesDetector:
    """_doc_references_detector scores files by broken-reference ratio."""

    def _metrics(self, references: list) -> FileMetrics:
        metrics = FileMetrics(
            name="guide.md",
            path="docs/guide.md",
            lines=10,
            classes=0,
            functions=0,
            imports=0,
        )
        metrics.custom_metrics["references"] = references
        return metrics

    def test_no_references_scores_100(self) -> None:
        result = _doc_references_detector(self._metrics([]), "", AnalysisConfig())
        assert result.score == 100.0
        assert result.findings == []

    def test_all_valid_references_scores_100(self, tmp_path: Path) -> None:
        (tmp_path / "packages" / "core").mkdir(parents=True)
        write_text_utf8(tmp_path / "packages" / "core" / "foo.py", "x = 1\n")
        refs = find_code_references("`packages/core/foo.py`", tmp_path)

        result = _doc_references_detector(self._metrics(refs), "", AnalysisConfig())

        assert result.score == 100.0
        assert result.findings == []

    def test_broken_reference_lowers_score_and_reports_finding(
        self, tmp_path: Path
    ) -> None:
        refs = find_code_references("`packages/core/missing.py`", tmp_path)

        result = _doc_references_detector(self._metrics(refs), "", AnalysisConfig())

        assert result.score == 0.0
        assert len(result.findings) == 1
        assert "packages/core/missing.py" in result.findings[0]

    def test_partial_broken_references_partial_score(self, tmp_path: Path) -> None:
        (tmp_path / "packages" / "core").mkdir(parents=True)
        write_text_utf8(tmp_path / "packages" / "core" / "foo.py", "x = 1\n")
        refs = find_code_references(
            "`packages/core/foo.py` and `packages/core/missing.py`", tmp_path
        )

        result = _doc_references_detector(self._metrics(refs), "", AnalysisConfig())

        assert result.score == 50.0


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A synthetic repo_root with docs/, packages/core/, tools/sdd-compile/."""
    root = tmp_path / "repo"
    (root / "packages" / "core" / "providence_core").mkdir(parents=True)
    write_text_utf8(
        root / "packages" / "core" / "providence_core" / "foo.py", "x = 1\n"
    )
    (root / "tools" / "sdd-compile" / "cmd").mkdir(parents=True)
    write_text_utf8(
        root / "tools" / "sdd-compile" / "cmd" / "main.go", "package main\n"
    )

    docs = root / "docs"
    docs.mkdir()
    write_text_utf8(
        docs / "guide.md",
        "# Guide\n\n"
        "Valid: `packages/core/providence_core/foo.py`\n\n"
        "Broken: `packages/core/providence_core/missing.py`\n\n"
        "Valid with line: `tools/sdd-compile/cmd/main.go:10`\n\n"
        "Broken: `tools/sdd-compile/cmd/missing.go`\n\n"
        "Bare mention (ignored): see packages/core/providence_core/foo.py directly.\n",
    )
    write_text_utf8(
        docs / "clean.md",
        "# Clean\n\nEverything here is fine: `packages/core/providence_core/foo.py`.\n",
    )

    return root


class TestAnalyzeAllEndToEnd:
    """analyze_all runs the full pipeline and writes the four report files."""

    def test_generates_report_files(self, repo: Path, tmp_path: Path) -> None:
        checker = DocReferenceChecker(
            AnalysisConfig(include_patterns=["**/*.md"]),
            output_dir=tmp_path / "out",
            repo_root=repo,
        )

        result = checker.analyze_all()

        out = tmp_path / "out"
        assert (out / "discovery.md").exists()
        assert (out / "analysis.md").exists()
        assert (out / "recommendations.md").exists()
        assert (out / "analysis.json").exists()
        assert result.summary["total_files"] == 2

    def test_flags_broken_references_and_ignores_bare_prose(
        self, repo: Path, tmp_path: Path
    ) -> None:
        checker = DocReferenceChecker(
            AnalysisConfig(include_patterns=["**/*.md"]),
            output_dir=tmp_path / "out",
            repo_root=repo,
        )

        checker.analyze_all()

        analysis = (tmp_path / "out" / "analysis.md").read_text(encoding="utf-8")
        recommendations = (tmp_path / "out" / "recommendations.md").read_text(
            encoding="utf-8"
        )

        assert "packages/core/providence_core/missing.py" in analysis
        assert "tools/sdd-compile/cmd/missing.go" in analysis
        assert "packages/core/providence_core/missing.py" in recommendations
        # the bare (non-backtick) prose mention must never be flagged
        assert analysis.count("packages/core/providence_core/foo.py") == 0

    def test_clean_file_has_no_findings(self, repo: Path, tmp_path: Path) -> None:
        checker = DocReferenceChecker(
            AnalysisConfig(include_patterns=["**/*.md"]),
            output_dir=tmp_path / "out",
            repo_root=repo,
        )

        checker.analyze_all()

        analysis = (tmp_path / "out" / "analysis.md").read_text(encoding="utf-8")
        assert "clean.md" not in analysis

    def test_no_writes_outside_output_dir(self, repo: Path, tmp_path: Path) -> None:
        """The checker is read-only over docs/, packages/core/, tools/sdd-compile/."""
        before = {
            p: p.read_text(encoding="utf-8") for p in repo.rglob("*") if p.is_file()
        }

        checker = DocReferenceChecker(
            AnalysisConfig(include_patterns=["**/*.md"]),
            output_dir=tmp_path / "out",
            repo_root=repo,
        )
        checker.analyze_all()

        after = {
            p: p.read_text(encoding="utf-8") for p in repo.rglob("*") if p.is_file()
        }
        assert before == after

    def test_analysis_json_structure(self, repo: Path, tmp_path: Path) -> None:
        checker = DocReferenceChecker(
            AnalysisConfig(include_patterns=["**/*.md"]),
            output_dir=tmp_path / "out",
            repo_root=repo,
        )

        checker.analyze_all()

        data = json.loads(
            (tmp_path / "out" / "analysis.json").read_text(encoding="utf-8")
        )
        assert data["analyzer_name"] == "doc_references"
        assert len(data["files"]) == 2
        guide_entry = next(f for f in data["files"] if f["name"] == "guide.md")
        assert len(guide_entry["references"]) == 4
        broken = [r for r in guide_entry["references"] if not r["exists"]]
        assert len(broken) == 2
