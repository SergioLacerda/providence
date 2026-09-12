"""TelemetryAnalyzer: guardrails analyzer for the providence_telemetry package.

Migrated from the standalone `tools/analysis/analyze_providence_telemetry.py` script
onto the guardrails core framework (see
`.analysis/pending/guardrails-framework-design.md`, Phase 3).
"""

from __future__ import annotations

import ast
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from providence_core.utils.text_io import write_json_utf8, write_text_utf8
from tools.guardrails.core.analyzer import GuardrailAnalyzer
from tools.guardrails.core.config import AnalysisConfig
from tools.guardrails.core.dimension import AnalysisDimension
from tools.guardrails.core.metrics import (
    DimensionResult,
    FileMetrics,
    compute_base_metrics,
)
from tools.guardrails.reporters.template import ReportTemplate

try:
    from tools.lib.providence_env import detect_repo_root
except ImportError:
    try:
        from providence_core.utils.environment import detect_repo_root
    except ImportError:

        def detect_repo_root() -> Path:
            current = Path.cwd()
            for parent in [current, *current.parents]:
                if (parent / ".providence").exists():
                    return parent
            return current


LONG_FUNCTION_LOOP_THRESHOLD = 20
GO_CANDIDATE_MIN_LINES = 5
GO_CANDIDATE_MAX_LINES = 50
GO_CANDIDATE_KEYWORDS = ["parse", "encode", "decode", "validate", "format", "hash"]


# --- AST / regex helpers -------------------------------------------------------


def find_hot_paths(functions: list[ast.FunctionDef]) -> list[str]:
    """Identify functions that are likely to be called frequently."""
    hot: list[str] = []

    for func in functions:
        func_name = func.name

        if "collect" in func_name or "emit" in func_name or "process" in func_name:
            hot.append(func_name)

        if func_name in ["__init__", "__call__", "execute", "run", "process"]:
            hot.append(func_name)

    return hot


def find_long_functions_with_loops(
    content: str, functions: list[ast.FunctionDef]
) -> list[str]:
    """Identify long functions that contain a `for` loop."""
    issues: list[str] = []
    for func in functions:
        func_lines = (func.end_lineno or func.lineno) - func.lineno + 1
        if (
            func_lines > LONG_FUNCTION_LOOP_THRESHOLD
            and "for "
            in content[
                content.find(func.name) : content.find(func.name) + func_lines * 40
            ]
        ):
            issues.append(f"long_function_with_loops: {func.name}")
    return issues


def find_performance_issues(
    content: str, functions: list[ast.FunctionDef]
) -> list[str]:
    """Identify potential performance bottlenecks via content heuristics."""
    issues: list[str] = []

    if (
        "for " in content
        and "for " in content[content.find("for") : content.find("for") + 500]
    ):
        issues.append("nested_loops")

    if content.count("isinstance(") > 5:
        issues.append("excessive_type_checking")

    if ".append(" in content and content.count(".append(") > 10:
        issues.append("frequent_list_appends")

    if content.count("str(") > 5 or content.count("json.dumps") > 2:
        issues.append("frequent_serialization")

    if "sleep" in content or "time.time()" in content:
        issues.append("timing_operations")

    if "regex" in content.lower() or "re.match" in content:
        issues.append("regex_matching")

    if "dict" not in content and ("get_" in content or "find_" in content):
        issues.append("missing_caching")

    issues.extend(find_long_functions_with_loops(content, functions))

    return sorted(set(issues))[:10]


def find_gaps(content: str, filename: str) -> list[str]:
    """Identify potential gaps (missing features, error handling, docs)."""
    gaps: list[str] = []

    if content.count("try:") == 0 and ("http" in filename or "network" in filename):
        gaps.append("missing_error_handling")

    if "assert " not in content and "raise " in content:
        gaps.append("missing_input_validation")

    if content.count("logger.") == 0 and content.count("log.") == 0:
        gaps.append("missing_logging")

    type_hint_count = content.count("->") + content.count(": ")
    if type_hint_count < 3:
        gaps.append("missing_type_hints")

    docstring_count = content.count('"""') + content.count("'''")
    if docstring_count < 2:
        gaps.append("missing_documentation")

    if (
        "threading" in content or "asyncio" in content
    ) and "lock" not in content.lower():
        gaps.append("possible_thread_safety_issue")

    if re.search(r"['\"]([a-zA-Z_]+)['\"]", content):
        magic_strings = len(re.findall(r"['\"]([a-zA-Z_]+)['\"]", content))
        if magic_strings > 10:
            gaps.append("hardcoded_strings")

    return gaps


def find_go_candidates(functions: list[ast.FunctionDef]) -> list[str]:
    """Identify functions that are good candidates for a Go rewrite."""
    candidates: list[str] = []

    for func in functions:
        func_lines = (func.end_lineno or func.lineno) - func.lineno + 1
        func_name = func.name

        if (
            GO_CANDIDATE_MIN_LINES < func_lines < GO_CANDIDATE_MAX_LINES
            and not any(x in func_name for x in ["__", "property", "_private"])
            and any(x in func_name for x in GO_CANDIDATE_KEYWORDS)
        ):
            candidates.append(func_name)

    return candidates


def extract_dependencies(imports: list[ast.Import | ast.ImportFrom]) -> list[str]:
    """Extract top-level external dependency names from imports."""
    deps: list[str] = []

    for imp in imports:
        if isinstance(imp, ast.Import):
            for alias in imp.names:
                deps.append(alias.name.split(".")[0])
        elif isinstance(imp, ast.ImportFrom) and imp.module:
            deps.append(imp.module.split(".")[0])

    return sorted(set(deps))


def identify_issues(content: str) -> list[str]:
    """Identify common bug patterns in the file content."""
    issues: list[str] = []

    if "except:" in content:
        issues.append("bare_except")

    if "== None" in content:
        issues.append("using_== None_instead_of_is_None")

    if "!= None" in content:
        issues.append("using_!=_None_instead_of_is_not_None")

    if ".split()" in content and ".split()[0]" in content:
        issues.append("unsafe_split_indexing")

    if "eval(" in content or "exec(" in content:
        issues.append("dangerous_eval_exec")

    if re.search(r"TODO|FIXME|HACK|BUG", content):
        todo_count = len(re.findall(r"TODO|FIXME|HACK|BUG", content))
        issues.append(f"code_comments_todos: {todo_count}")

    if "global " in content:
        issues.append("uses_global_state")

    if (
        ("threading" in content or "asyncio" in content)
        and "Queue" not in content
        and "Lock" not in content
    ):
        issues.append("potential_race_condition")

    return issues


# --- dimensions: performance ------------------------------------------------------


def _performance_detector(
    metrics: FileMetrics, content: str, config: AnalysisConfig
) -> DimensionResult:
    findings: list[str] = metrics.custom_metrics.get("performance_issues", [])
    hot_paths: list[str] = metrics.custom_metrics.get("hot_paths", [])

    score = 100.0 - min(60, len(findings) * 10)

    return DimensionResult(
        name="performance",
        findings=findings,
        score=max(0.0, score),
        metadata={"hot_paths": hot_paths},
    )


def _performance_reporter(result: DimensionResult, template: ReportTemplate) -> str:
    parts = [
        template.bullet_list(result.findings)
        if result.findings
        else "No performance issues found."
    ]
    hot_paths = result.metadata.get("hot_paths", [])
    if hot_paths:
        parts.append("Hot paths: " + ", ".join(f"`{name}`" for name in hot_paths))

    body = "\n\n".join(parts)
    return template.section(
        f"Performance (score: {result.score:.0f}/100)", body, level=4
    )


# --- dimensions: gaps & bugs ---------------------------------------------------------


def _gaps_detector(
    metrics: FileMetrics, content: str, config: AnalysisConfig
) -> DimensionResult:
    gaps: list[str] = metrics.custom_metrics.get("gaps", [])
    issues: list[str] = metrics.custom_metrics.get("issues", [])

    findings = [*gaps, *issues]
    score = 100.0 - min(50, len(gaps) * 8) - min(30, len(issues) * 6)

    return DimensionResult(
        name="gaps",
        findings=findings,
        score=max(0.0, score),
        metadata={"gaps": gaps, "issues": issues},
    )


def _gaps_reporter(result: DimensionResult, template: ReportTemplate) -> str:
    body = (
        template.bullet_list(result.findings)
        if result.findings
        else "No gaps or issues found."
    )
    return template.section(
        f"Gaps & Bugs (score: {result.score:.0f}/100)", body, level=4
    )


# --- dimensions: go feasibility -------------------------------------------------------


def _go_feasibility_detector(
    metrics: FileMetrics, content: str, config: AnalysisConfig
) -> DimensionResult:
    go_candidates: list[str] = metrics.custom_metrics.get("go_candidates", [])

    findings = [f"Go candidate: {name}" for name in go_candidates]
    score = min(100.0, len(go_candidates) * 15.0)

    return DimensionResult(
        name="go_feasibility",
        findings=findings,
        score=score,
        metadata={"go_candidates": go_candidates},
    )


def _go_feasibility_reporter(result: DimensionResult, template: ReportTemplate) -> str:
    body = (
        template.bullet_list(result.findings)
        if result.findings
        else "No Go-rewrite candidates found."
    )
    return template.section(
        f"Go Feasibility (score: {result.score:.0f}/100)", body, level=4
    )


# --- analyzer ------------------------------------------------------------------------


def _dimension_title(name: str) -> str:
    return name.replace("_", " ").title()


class TelemetryAnalyzer(GuardrailAnalyzer):
    """Analyzes the providence_telemetry package across three dimensions."""

    def __init__(
        self,
        config: AnalysisConfig,
        output_dir: Path | None = None,
        target_dir: Path | None = None,
    ) -> None:
        self._target_dir = target_dir or (
            detect_repo_root()
            / "packages"
            / "core"
            / "providence_telemetry"
            / "src"
            / "providence_telemetry"
        )
        super().__init__(config, output_dir)

    def get_target_directory(self) -> Path:
        return self._target_dir

    def get_analysis_name(self) -> str:
        return "providence_telemetry"

    def get_dimensions(self) -> list[AnalysisDimension]:
        return [
            AnalysisDimension(
                "performance",
                _performance_detector,
                _performance_reporter,
                description="Hot paths and potential performance bottlenecks.",
                icon="⚡",
            ),
            AnalysisDimension(
                "gaps",
                _gaps_detector,
                _gaps_reporter,
                description="Missing error handling, validation, logging, docs, and bugs.",
                icon="\U0001f573️",
            ),
            AnalysisDimension(
                "go_feasibility",
                _go_feasibility_detector,
                _go_feasibility_reporter,
                description="Functions that are good candidates for a Go rewrite.",
                icon="\U0001f680",
            ),
        ]

    def create_file_metrics(self, file_path: Path, content: str) -> FileMetrics:
        metrics = compute_base_metrics(file_path, content)

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return metrics

        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        imports = [
            n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)
        ]

        metrics.custom_metrics["hot_paths"] = find_hot_paths(functions)
        metrics.custom_metrics["performance_issues"] = find_performance_issues(
            content, functions
        )
        metrics.custom_metrics["gaps"] = find_gaps(content, file_path.name)
        metrics.custom_metrics["go_candidates"] = find_go_candidates(functions)
        metrics.custom_metrics["dependencies"] = extract_dependencies(imports)
        metrics.custom_metrics["issues"] = identify_issues(content)

        return metrics

    def _generate_reports(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        write_text_utf8(self.output_dir / "discovery.md", self._render_discovery())
        write_text_utf8(self.output_dir / "analysis.md", self._render_analysis())
        write_text_utf8(
            self.output_dir / "recommendations.md", self._render_recommendations()
        )
        write_json_utf8(self.output_dir / "analysis.json", self._build_raw_data())

    def _render_discovery(self) -> str:
        assert self.results is not None
        template = ReportTemplate()
        summary = self.results.summary
        dimensions = self.get_dimensions()

        summary_items = [f"Total files: {summary['total_files']}"]
        for dimension in dimensions:
            dim_summary = summary.get(dimension.name, {})
            summary_items.append(
                f"{dimension.icon} {_dimension_title(dimension.name)}: avg score "
                f"{dim_summary.get('avg_score', 0.0):.1f}/100, "
                f"{dim_summary.get('files_with_issues', 0)} file(s) with findings"
            )

        sections = [
            template.header("Providence Telemetry Module - Discovery Report"),
            f"**Timestamp**: {self.results.timestamp}",
            template.section("Executive Summary", template.bullet_list(summary_items)),
        ]

        if self.files:
            headers = ["File", "Lines", *[d.name for d in dimensions]]
            rows = [
                [
                    f.name,
                    str(f.lines),
                    *[f"{f.dimension_results[d.name].score:.0f}" for d in dimensions],
                ]
                for f in sorted(self.files, key=lambda fm: fm.lines, reverse=True)
            ]
            sections.append(template.section("Files", template.table(headers, rows)))

        return "\n\n".join(sections)

    def _render_analysis(self) -> str:
        template = ReportTemplate()
        sections = [template.header("Providence Telemetry Module - Detailed Analysis")]

        for dimension in self.get_dimensions():
            file_sections = []
            for file in self.files:
                result = file.dimension_results.get(dimension.name)
                if result and result.findings:
                    file_sections.append(
                        f"**`{file.name}`**\n\n" + dimension.report(result, template)
                    )

            body = "\n\n".join(file_sections) if file_sections else "No findings."
            sections.append(
                template.section(
                    f"{dimension.icon} {_dimension_title(dimension.name)}",
                    body,
                    level=2,
                )
            )

        return "\n\n".join(sections)

    def _render_recommendations(self) -> str:
        template = ReportTemplate()
        sections = [template.header("Providence Telemetry Module - Recommendations")]

        for dimension in self.get_dimensions():
            files_with_findings = [
                f
                for f in self.files
                if dimension.name in f.dimension_results
                and f.dimension_results[dimension.name].findings
            ]
            reverse = dimension.name == "go_feasibility"
            worst = sorted(
                files_with_findings,
                key=lambda f: f.dimension_results[dimension.name].score,
                reverse=reverse,
            )[:5]

            items = [
                f"`{f.name}` (score {f.dimension_results[dimension.name].score:.0f}/100): "
                + "; ".join(f.dimension_results[dimension.name].findings)
                for f in worst
            ]
            body = template.bullet_list(items) if items else "No action needed."
            sections.append(
                template.section(
                    f"{dimension.icon} {_dimension_title(dimension.name)}",
                    body,
                    level=2,
                )
            )

        return "\n\n".join(sections)

    def _build_raw_data(self) -> dict[str, Any]:
        assert self.results is not None
        return {
            "analyzer_name": self.results.analyzer_name,
            "timestamp": self.results.timestamp,
            "files": [asdict(f) for f in self.files],
            "summary": self.results.summary,
        }
