"""Unit tests for tools.guardrails.analyzers.telemetry."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from tools.guardrails.analyzers.telemetry import (
    TelemetryAnalyzer,
    _gaps_detector,
    _go_feasibility_detector,
    _performance_detector,
    extract_dependencies,
    find_gaps,
    find_go_candidates,
    find_hot_paths,
    find_long_functions_with_loops,
    find_performance_issues,
    identify_issues,
)
from tools.guardrails.core.config import AnalysisConfig
from tools.guardrails.core.metrics import FileMetrics

pytestmark = pytest.mark.unit


def _parse_functions(content: str) -> list[ast.FunctionDef]:
    tree = ast.parse(content)
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _parse_imports(content: str) -> list[ast.Import | ast.ImportFrom]:
    tree = ast.parse(content)
    return [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)]


class TestFindHotPaths:
    """find_hot_paths flags functions on hot-path naming conventions."""

    def test_detects_name_substring_hot_paths(self) -> None:
        content = (
            "def collect_metrics():\n    pass\n\n"
            "def emit_event():\n    pass\n\n"
            "def other():\n    pass\n"
        )
        functions = _parse_functions(content)
        assert find_hot_paths(functions) == ["collect_metrics", "emit_event"]

    def test_detects_exact_name_hot_paths(self) -> None:
        content = "def __init__(self):\n    pass\n\ndef run():\n    pass\n"
        functions = _parse_functions(content)
        assert find_hot_paths(functions) == ["__init__", "run"]

    def test_no_hot_paths(self) -> None:
        functions = _parse_functions("def helper():\n    pass\n")
        assert find_hot_paths(functions) == []


class TestFindLongFunctionsWithLoops:
    """find_long_functions_with_loops flags large functions containing loops."""

    def test_detects_long_function_with_loop(self) -> None:
        body = "\n".join(f"    x{i} = {i}" for i in range(25))
        content = f"def big_func():\n{body}\n    for i in range(10):\n        pass\n"
        functions = _parse_functions(content)

        result = find_long_functions_with_loops(content, functions)

        assert result == ["long_function_with_loops: big_func"]

    def test_short_function_with_loop_not_flagged(self) -> None:
        content = "def small_func():\n    for i in range(10):\n        pass\n"
        functions = _parse_functions(content)

        assert find_long_functions_with_loops(content, functions) == []


class TestFindPerformanceIssues:
    """find_performance_issues detects common performance anti-patterns."""

    def test_detects_multiple_performance_issues(self) -> None:
        content = (
            "for item in items:\n"
            "    for sub in item:\n"
            "        pass\n"
            + "x = isinstance(v, int)\n" * 6
            + "result.append(1)\n" * 11
            + "y = str(v)\n" * 6
            + "time.sleep(1)\n"
            + "re.match(pattern, v)\n"
            + "get_value()\n"
        )
        functions = _parse_functions(content)

        result = find_performance_issues(content, functions)

        assert result == sorted(
            {
                "nested_loops",
                "excessive_type_checking",
                "frequent_list_appends",
                "frequent_serialization",
                "timing_operations",
                "regex_matching",
                "missing_caching",
            }
        )

    def test_clean_content_no_performance_issues(self) -> None:
        content = "x = 1\n"
        functions = _parse_functions(content)

        assert find_performance_issues(content, functions) == []


class TestFindGaps:
    """find_gaps detects missing best-practice patterns."""

    def test_missing_error_handling_for_http_file(self) -> None:
        content = "def fetch():\n    pass\n"
        assert "missing_error_handling" in find_gaps(content, "http_client.py")

    def test_no_missing_error_handling_when_try_present(self) -> None:
        content = "def fetch():\n    try:\n        pass\n    except Exception:\n        pass\n"
        assert "missing_error_handling" not in find_gaps(content, "http_client.py")

    def test_missing_input_validation(self) -> None:
        content = (
            "def f(x):\n    if x < 0:\n        raise ValueError('bad')\n    return x\n"
        )
        assert "missing_input_validation" in find_gaps(content, "module.py")

    def test_missing_logging(self) -> None:
        content = "def f():\n    return 1\n"
        assert "missing_logging" in find_gaps(content, "module.py")

    def test_missing_type_hints(self) -> None:
        content = "def f(x):\n    return x\n"
        assert "missing_type_hints" in find_gaps(content, "module.py")

    def test_missing_documentation(self) -> None:
        content = "def f(x: int) -> int:\n    return x\n"
        assert "missing_documentation" in find_gaps(content, "module.py")

    def test_no_missing_type_hints_or_docs_when_present(self) -> None:
        content = (
            '"""Module."""\n\n'
            "def f(x: int, y: int) -> int:\n"
            '    """Add two numbers."""\n'
            "    return x + y\n"
        )

        result = find_gaps(content, "module.py")

        assert "missing_type_hints" not in result
        assert "missing_documentation" not in result

    def test_possible_thread_safety_issue(self) -> None:
        content = "import threading\ndef f():\n    pass\n"
        assert "possible_thread_safety_issue" in find_gaps(content, "module.py")

    def test_hardcoded_strings(self) -> None:
        content = "\n".join(f'x{i} = "value"' for i in range(11))
        assert "hardcoded_strings" in find_gaps(content, "module.py")


class TestFindGoCandidates:
    """find_go_candidates flags small pure-computation functions."""

    def test_detects_go_candidate(self) -> None:
        body = "\n".join(f"    x{i} = {i}" for i in range(8))
        content = f"def parse_data():\n{body}\n    return x0\n"
        functions = _parse_functions(content)

        assert find_go_candidates(functions) == ["parse_data"]

    def test_excludes_dunder_and_too_short(self) -> None:
        content = "def __init__(self):\n    pass\n\ndef parse_x():\n    return 1\n"
        functions = _parse_functions(content)

        assert find_go_candidates(functions) == []

    def test_excludes_too_long_function(self) -> None:
        body = "\n".join(f"    x{i} = {i}" for i in range(55))
        content = f"def parse_data():\n{body}\n"
        functions = _parse_functions(content)

        assert find_go_candidates(functions) == []


class TestExtractDependencies:
    """extract_dependencies returns top-level imported module names."""

    def test_extracts_top_level_module_names(self) -> None:
        imports = _parse_imports(
            "import os.path\nfrom collections import OrderedDict\n"
        )

        assert extract_dependencies(imports) == ["collections", "os"]


class TestIdentifyIssues:
    """identify_issues flags common bug patterns."""

    def test_detects_bare_except(self) -> None:
        assert "bare_except" in identify_issues("try:\n    pass\nexcept:\n    pass\n")

    def test_detects_none_comparisons(self) -> None:
        result = identify_issues("if x == None:\n    pass\nif y != None:\n    pass\n")

        assert "using_== None_instead_of_is_None" in result
        assert "using_!=_None_instead_of_is_not_None" in result

    def test_detects_unsafe_split_indexing(self) -> None:
        content = "parts = s.split()\nfirst = s.split()[0]\n"
        assert "unsafe_split_indexing" in identify_issues(content)

    def test_detects_eval_exec(self) -> None:
        assert "dangerous_eval_exec" in identify_issues("eval('1+1')\n")

    def test_detects_todo_comments(self) -> None:
        result = identify_issues("# TODO: fix this\n# FIXME later\n")

        assert "code_comments_todos: 2" in result

    def test_detects_global_state(self) -> None:
        assert "uses_global_state" in identify_issues("global counter\ncounter = 1\n")

    def test_detects_potential_race_condition(self) -> None:
        assert "potential_race_condition" in identify_issues("import threading\n")

    def test_no_race_condition_when_lock_used(self) -> None:
        result = identify_issues("import threading\nlock = threading.Lock()\n")

        assert "potential_race_condition" not in result

    def test_clean_content_no_issues(self) -> None:
        assert identify_issues("x = 1\n") == []


class TestCreateFileMetrics:
    """create_file_metrics populates custom_metrics with all derived data."""

    def test_populates_custom_metrics(self, tmp_path: Path) -> None:
        analyzer = TelemetryAnalyzer(
            AnalysisConfig(), output_dir=tmp_path / "out", target_dir=tmp_path / "pkg"
        )
        content = "def process_event():\n    isinstance(1, int)\n"

        metrics = analyzer.create_file_metrics(Path("module.py"), content)

        assert metrics.custom_metrics["hot_paths"] == ["process_event"]
        assert "performance_issues" in metrics.custom_metrics
        assert "gaps" in metrics.custom_metrics
        assert "go_candidates" in metrics.custom_metrics
        assert "dependencies" in metrics.custom_metrics
        assert "issues" in metrics.custom_metrics


class TestPerformanceDetector:
    """_performance_detector scores files on performance issue counts."""

    def test_clean_file(self) -> None:
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=10, classes=0, functions=1, imports=0
        )
        metrics.custom_metrics["performance_issues"] = []
        metrics.custom_metrics["hot_paths"] = []

        result = _performance_detector(metrics, "content", AnalysisConfig())

        assert result.findings == []
        assert result.score == 100.0

    def test_with_issues_and_hot_paths(self) -> None:
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=10, classes=0, functions=1, imports=0
        )
        metrics.custom_metrics["performance_issues"] = [
            "nested_loops",
            "excessive_type_checking",
        ]
        metrics.custom_metrics["hot_paths"] = ["run"]

        result = _performance_detector(metrics, "content", AnalysisConfig())

        assert result.findings == ["nested_loops", "excessive_type_checking"]
        assert result.score == 80.0
        assert result.metadata["hot_paths"] == ["run"]


class TestGapsDetector:
    """_gaps_detector combines gaps and issues into a single dimension."""

    def test_clean_file(self) -> None:
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=10, classes=0, functions=1, imports=0
        )
        metrics.custom_metrics["gaps"] = []
        metrics.custom_metrics["issues"] = []

        result = _gaps_detector(metrics, "content", AnalysisConfig())

        assert result.findings == []
        assert result.score == 100.0

    def test_with_gaps_and_issues(self) -> None:
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=10, classes=0, functions=1, imports=0
        )
        metrics.custom_metrics["gaps"] = ["missing_logging"]
        metrics.custom_metrics["issues"] = ["bare_except"]

        result = _gaps_detector(metrics, "content", AnalysisConfig())

        assert result.findings == ["missing_logging", "bare_except"]
        assert result.score == 100 - 8 - 6


class TestGoFeasibilityDetector:
    """_go_feasibility_detector scores files on Go-rewrite opportunity."""

    def test_no_candidates(self) -> None:
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=10, classes=0, functions=1, imports=0
        )
        metrics.custom_metrics["go_candidates"] = []

        result = _go_feasibility_detector(metrics, "content", AnalysisConfig())

        assert result.findings == []
        assert result.score == 0.0

    def test_with_candidates(self) -> None:
        metrics = FileMetrics(
            name="a.py", path="a.py", lines=10, classes=0, functions=1, imports=0
        )
        metrics.custom_metrics["go_candidates"] = ["parse_x", "encode_y"]

        result = _go_feasibility_detector(metrics, "content", AnalysisConfig())

        assert result.findings == ["Go candidate: parse_x", "Go candidate: encode_y"]
        assert result.score == 30.0


@pytest.fixture
def project(tmp_path: Path) -> Path:
    pkg = tmp_path / "pkg"
    pkg.mkdir()

    perf_content = (
        "for item in items:\n"
        "    for sub in item:\n"
        "        pass\n"
        + "x = isinstance(v, int)\n" * 6
        + "result.append(1)\n" * 11
        + "y = str(v)\n" * 6
        + "time.sleep(1)\n"
        + "re.match(pattern, v)\n"
        + "get_value()\n"
    )
    (pkg / "perf_module.py").write_text(perf_content, encoding="utf-8")

    validate_body = "\n".join(f"    y{i} = {i}" for i in range(8))
    gaps_content = (
        "try:\n"
        "    pass\n"
        "except:\n"
        "    pass\n"
        "if x == None:\n"
        "    pass\n"
        "\n"
        "def validate_input():\n"
        f"{validate_body}\n"
        "    return True\n"
    )
    (pkg / "gaps_module.py").write_text(gaps_content, encoding="utf-8")

    go_body = "\n".join(f"    x{i} = {i}" for i in range(8))
    go_content = (
        f"def parse_data():\n{go_body}\n    return x0\n\n"
        f"def encode_value():\n{go_body}\n    return x0\n"
    )
    (pkg / "go_module.py").write_text(go_content, encoding="utf-8")

    return pkg


class TestAnalyzeAllEndToEnd:
    """analyze_all runs the full pipeline and writes the four report files."""

    def test_generates_report_files(self, project: Path, tmp_path: Path) -> None:
        analyzer = TelemetryAnalyzer(
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
        analyzer = TelemetryAnalyzer(
            AnalysisConfig(), output_dir=tmp_path / "out", target_dir=project
        )

        analyzer.analyze_all()

        data = json.loads(
            (tmp_path / "out" / "analysis.json").read_text(encoding="utf-8")
        )
        assert data["analyzer_name"] == "providence_telemetry"
        assert set(data["summary"]) >= {
            "total_files",
            "performance",
            "gaps",
            "go_feasibility",
        }
        assert len(data["files"]) == 3

    def test_discovery_and_analysis_content(
        self, project: Path, tmp_path: Path
    ) -> None:
        analyzer = TelemetryAnalyzer(
            AnalysisConfig(), output_dir=tmp_path / "out", target_dir=project
        )

        analyzer.analyze_all()

        discovery = (tmp_path / "out" / "discovery.md").read_text(encoding="utf-8")
        analysis = (tmp_path / "out" / "analysis.md").read_text(encoding="utf-8")

        assert "perf_module.py" in discovery
        assert "nested_loops" in analysis
        assert "bare_except" in analysis
        assert "Go candidate: parse_data" in analysis

    def test_go_feasibility_recommendations_sorted_by_viability_desc(
        self, project: Path, tmp_path: Path
    ) -> None:
        analyzer = TelemetryAnalyzer(
            AnalysisConfig(), output_dir=tmp_path / "out", target_dir=project
        )

        analyzer.analyze_all()

        recommendations = (tmp_path / "out" / "recommendations.md").read_text(
            encoding="utf-8"
        )
        go_section = recommendations[recommendations.index("Go Feasibility") :]

        go_idx = go_section.find("go_module.py")
        gaps_idx = go_section.find("gaps_module.py")

        assert go_idx != -1
        assert gaps_idx != -1
        assert go_idx < gaps_idx
