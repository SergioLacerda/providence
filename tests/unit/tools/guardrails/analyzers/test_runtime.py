"""Unit tests for tools.guardrails.analyzers.runtime."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from tools.guardrails.analyzers.runtime import (
    RuntimeAnalyzer,
    _performance_detector,
    _refactoring_detector,
    _standardization_detector,
    find_circular_deps,
    find_hardcoded_values,
    find_heavy_imports,
    find_long_functions,
    register_runtime_patterns,
)
from tools.guardrails.core.config import AnalysisConfig
from tools.guardrails.core.metrics import FileMetrics
from tools.guardrails.core.patterns import PatternRegistry

pytestmark = pytest.mark.unit


def _parse_imports(content: str) -> list[ast.Import | ast.ImportFrom]:
    tree = ast.parse(content)
    return [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)]


@pytest.fixture(autouse=True)
def _reset_pattern_registry():
    PatternRegistry._instance = None
    yield
    PatternRegistry._instance = None


class TestFindHeavyImports:
    """find_heavy_imports flags imports of known heavy modules."""

    def test_detects_heavy_module_import(self) -> None:
        imports = _parse_imports("import pandas as pd\nimport os\n")
        assert find_heavy_imports(imports) == ["pandas"]

    def test_detects_heavy_from_import(self) -> None:
        imports = _parse_imports(
            "from sklearn.linear_model import LogisticRegression\n"
        )
        assert find_heavy_imports(imports) == ["sklearn.linear_model"]

    def test_no_heavy_imports(self) -> None:
        imports = _parse_imports("import os\nimport sys\n")
        assert find_heavy_imports(imports) == []


class TestFindCircularDeps:
    """find_circular_deps flags providence_runtime imports other than self-imports."""

    def test_detects_circular_dep(self) -> None:
        imports = _parse_imports("from providence_runtime.bar import Baz\n")
        deps = find_circular_deps(Path("foo.py"), imports)
        assert deps == ["providence_runtime.bar"]

    def test_self_import_not_circular(self) -> None:
        imports = _parse_imports("from providence_runtime.foo import something\n")
        deps = find_circular_deps(Path("foo.py"), imports)
        assert deps == []

    def test_no_providence_runtime_imports(self) -> None:
        imports = _parse_imports("import os\n")
        assert find_circular_deps(Path("foo.py"), imports) == []


class TestFindLongFunctions:
    """find_long_functions returns functions exceeding the configured threshold."""

    def test_detects_long_function(self) -> None:
        content = "def f():\n" + "    x = 1\n" * 35
        tree = ast.parse(content)
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]

        result = find_long_functions(functions, 30)

        assert len(result) == 1
        assert result[0]["name"] == "f"
        assert result[0]["lines"] > 30

    def test_no_long_functions(self) -> None:
        content = "def f():\n    x = 1\n"
        tree = ast.parse(content)
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]

        assert find_long_functions(functions, 30) == []


class TestFindHardcodedValues:
    """find_hardcoded_values flags magic numbers, repeated strings, and URLs."""

    def test_detects_magic_number(self) -> None:
        result = find_hardcoded_values("TIMEOUT = 1024\n")
        assert "magic_number: 1024" in result

    def test_detects_repeated_string(self) -> None:
        content = 'a = "duplicated value string!!"\nb = "duplicated value string!!"\n'
        result = find_hardcoded_values(content)
        assert any(v.startswith("repeated_string:") for v in result)

    def test_detects_hardcoded_url(self) -> None:
        result = find_hardcoded_values('url = "http://example.com"\n')
        assert "hardcoded_urls" in result

    def test_clean_content_has_no_findings(self) -> None:
        assert find_hardcoded_values("x = 1\n") == []


class TestRegisterRuntimePatterns:
    """register_runtime_patterns registers standardization heuristics."""

    def test_registers_standardization_group(self) -> None:
        register_runtime_patterns()
        registry = PatternRegistry()

        assert "duplicate_imports" in registry.pattern_groups["standardization"]
        assert "multiple_conditionals" in registry.pattern_groups["standardization"]

    def test_duplicate_imports_pattern_matches(self) -> None:
        register_runtime_patterns()
        content = "import os\nimport os\n"

        matches = PatternRegistry().find_matches(content, group="standardization")

        assert "duplicate_imports" in matches

    def test_multiple_conditionals_pattern_matches(self) -> None:
        register_runtime_patterns()
        content = "\n".join(f"if x == {i}:" for i in range(6))

        matches = PatternRegistry().find_matches(content, group="standardization")

        assert "multiple_conditionals" in matches


class TestCreateFileMetrics:
    """create_file_metrics populates custom_metrics with all derived data."""

    def test_populates_custom_metrics(self, tmp_path: Path) -> None:
        analyzer = RuntimeAnalyzer(
            AnalysisConfig(), output_dir=tmp_path / "out", target_dir=tmp_path / "pkg"
        )
        content = "import pandas\n\ndef f():\n" + "    x = 1\n" * 35

        metrics = analyzer.create_file_metrics(Path("module.py"), content)

        assert metrics.custom_metrics["heavy_imports"] == ["pandas"]
        assert len(metrics.custom_metrics["long_functions"]) == 1
        assert metrics.custom_metrics["circular_deps"] == []
        assert metrics.custom_metrics["hardcoded_values"] == []
        assert metrics.custom_metrics["duplicate_patterns"] == []


class TestRefactoringDetector:
    """_refactoring_detector flags overly long files and functions."""

    def test_clean_file(self) -> None:
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=50, classes=1, functions=2, imports=1
        )
        metrics.custom_metrics["long_functions"] = []

        result = _refactoring_detector(metrics, "content", AnalysisConfig())

        assert result.findings == []
        assert result.score == 100.0

    def test_long_file_and_function(self) -> None:
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=250, classes=0, functions=1, imports=1
        )
        metrics.custom_metrics["long_functions"] = [
            {"name": "f", "lines": 40, "params": 0}
        ]

        result = _refactoring_detector(metrics, "content", AnalysisConfig())

        assert "File too long (250 lines)" in result.findings
        assert "Function 'f' too long (40 lines)" in result.findings
        assert result.score < 100.0


class TestPerformanceDetector:
    """_performance_detector flags heavy imports and circular dependencies."""

    def test_clean_file(self) -> None:
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=10, classes=0, functions=1, imports=1
        )
        metrics.custom_metrics["heavy_imports"] = []
        metrics.custom_metrics["circular_deps"] = []

        result = _performance_detector(metrics, "content", AnalysisConfig())

        assert result.findings == []
        assert result.score == 100.0

    def test_heavy_imports_and_circular_deps(self) -> None:
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=10, classes=0, functions=1, imports=1
        )
        metrics.custom_metrics["heavy_imports"] = ["pandas"]
        metrics.custom_metrics["circular_deps"] = ["providence_runtime.other"]

        result = _performance_detector(metrics, "content", AnalysisConfig())

        assert "Heavy import: pandas" in result.findings
        assert "Circular dependency: providence_runtime.other" in result.findings
        assert result.score == 100 - 10 - 15


class TestStandardizationDetector:
    """_standardization_detector flags hardcoded values and duplicate patterns."""

    def test_clean_file(self) -> None:
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=10, classes=0, functions=1, imports=1
        )
        metrics.custom_metrics["hardcoded_values"] = []
        metrics.custom_metrics["duplicate_patterns"] = []

        result = _standardization_detector(metrics, "content", AnalysisConfig())

        assert result.findings == []
        assert result.score == 100.0

    def test_hardcoded_values_and_duplicate_patterns(self) -> None:
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=10, classes=0, functions=1, imports=1
        )
        metrics.custom_metrics["hardcoded_values"] = ["magic_number: 1024"]
        metrics.custom_metrics["duplicate_patterns"] = ["multiple_conditionals"]

        result = _standardization_detector(metrics, "content", AnalysisConfig())

        assert "magic_number: 1024" in result.findings
        assert "multiple_conditionals" in result.findings
        assert result.score == 100 - 5 - 10


@pytest.fixture
def project(tmp_path: Path) -> Path:
    pkg = tmp_path / "pkg"
    pkg.mkdir()

    long_content = "def big_function():\n" + "    x = 1\n" * 250
    (pkg / "big_module.py").write_text(long_content, encoding="utf-8")

    (pkg / "heavy_module.py").write_text(
        "import pandas as pd\n\n\ndef use_pandas():\n    return pd.DataFrame()\n",
        encoding="utf-8",
    )

    std_content = (
        "TIMEOUT = 1024\n"
        'URL = "http://example.com"\n'
        'A = "duplicated value string!!"\n'
        'B = "duplicated value string!!"\n'
    )
    (pkg / "std_module.py").write_text(std_content, encoding="utf-8")

    return pkg


class TestAnalyzeAllEndToEnd:
    """analyze_all runs the full pipeline and writes the four report files."""

    def test_generates_report_files(self, project: Path, tmp_path: Path) -> None:
        analyzer = RuntimeAnalyzer(
            AnalysisConfig(), output_dir=tmp_path / "out", target_dir=project
        )

        result = analyzer.analyze_all()

        out = tmp_path / "out"
        assert (out / "discovery.md").exists()
        assert (out / "analysis.md").exists()
        assert (out / "recommendations.md").exists()
        assert (out / "analysis.json").exists()
        assert result.summary["total_files"] == 3

    def test_analysis_json_structure(self, project: Path, tmp_path: Path) -> None:
        analyzer = RuntimeAnalyzer(
            AnalysisConfig(), output_dir=tmp_path / "out", target_dir=project
        )

        analyzer.analyze_all()

        data = json.loads(
            (tmp_path / "out" / "analysis.json").read_text(encoding="utf-8")
        )
        assert data["analyzer_name"] == "providence_runtime"
        assert set(data["summary"]) >= {
            "total_files",
            "refactoring",
            "performance",
            "standardization",
        }
        assert len(data["files"]) == 3

    def test_discovery_and_analysis_content(
        self, project: Path, tmp_path: Path
    ) -> None:
        analyzer = RuntimeAnalyzer(
            AnalysisConfig(), output_dir=tmp_path / "out", target_dir=project
        )

        analyzer.analyze_all()

        discovery = (tmp_path / "out" / "discovery.md").read_text(encoding="utf-8")
        analysis = (tmp_path / "out" / "analysis.md").read_text(encoding="utf-8")

        assert "big_module.py" in discovery
        assert "File too long" in analysis
        assert "Heavy import: pandas" in analysis
        assert "magic_number: 1024" in analysis
