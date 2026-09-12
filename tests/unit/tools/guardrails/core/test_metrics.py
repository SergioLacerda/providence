"""Unit tests for tools.guardrails.core.metrics."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.guardrails.core.metrics import (
    AnalysisResult,
    DimensionResult,
    FileMetrics,
    compute_base_metrics,
)

pytestmark = pytest.mark.unit


class TestDimensionResult:
    """Default values for DimensionResult."""

    def test_defaults(self) -> None:
        result = DimensionResult(name="refactoring")
        assert result.findings == []
        assert result.score == 0.0
        assert result.metadata == {}


class TestFileMetrics:
    """Default values and field shapes for FileMetrics."""

    def test_defaults(self) -> None:
        metrics = FileMetrics(
            name="foo.py",
            path="pkg/foo.py",
            lines=10,
            classes=1,
            functions=2,
            imports=3,
        )
        assert metrics.has_issues is False
        assert metrics.dimension_results == {}
        assert metrics.custom_metrics == {}


class TestAnalysisResult:
    """Default values for AnalysisResult."""

    def test_defaults(self) -> None:
        result = AnalysisResult(
            analyzer_name="providence_runtime", timestamp="2026-06-12T00:00:00"
        )
        assert result.files == []
        assert result.summary == {}


class TestComputeBaseMetrics:
    """compute_base_metrics derives counts via AST."""

    def test_counts_classes_functions_imports_lines(self) -> None:
        content = (
            "import os\n"
            "from pathlib import Path\n"
            "\n"
            "class Foo:\n"
            "    def bar(self):\n"
            "        return os.getcwd()\n"
            "\n"
            "def baz():\n"
            "    return Path('.')\n"
        )
        metrics = compute_base_metrics(Path("pkg/foo.py"), content)

        assert metrics.name == "foo.py"
        assert metrics.path == "pkg/foo.py"
        assert metrics.lines == len(content.splitlines())
        assert metrics.classes == 1
        assert (
            metrics.functions == 2
        )  # bar + baz (method counts as function via ast.walk)
        assert metrics.imports == 2

    def test_empty_file(self) -> None:
        metrics = compute_base_metrics(Path("empty.py"), "")
        assert metrics.lines == 0
        assert metrics.classes == 0
        assert metrics.functions == 0
        assert metrics.imports == 0
