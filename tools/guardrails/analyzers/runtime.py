"""RuntimeAnalyzer: guardrails analyzer for the providence_runtime package.

Migrated from the standalone `tools/analysis/analyze_providence_runtime.py` script
onto the guardrails core framework (see
`.analysis/pending/guardrails-framework-design.md`, Phase 2).
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
from tools.guardrails.core.patterns import Pattern, PatternRegistry, PatternType
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


HEAVY_MODULES = ["pandas", "numpy", "sklearn", "tensorflow", "torch", "cv2"]


# --- AST / regex helpers -------------------------------------------------------


def find_heavy_imports(imports: list[ast.Import | ast.ImportFrom]) -> list[str]:
    """Identify imports of known heavy modules (pandas, numpy, etc.)."""
    heavy: list[str] = []
    for imp in imports:
        if isinstance(imp, ast.Import):
            for alias in imp.names:
                if any(h in alias.name for h in HEAVY_MODULES):
                    heavy.append(alias.name)
        elif (
            isinstance(imp, ast.ImportFrom)
            and imp.module
            and any(h in imp.module for h in HEAVY_MODULES)
        ):
            heavy.append(imp.module)
    return sorted(set(heavy))


def find_circular_deps(
    file_path: Path, imports: list[ast.Import | ast.ImportFrom]
) -> list[str]:
    """Detect potential circular dependencies via self-package imports."""
    circular: list[str] = []
    file_name = file_path.stem

    for imp in imports:
        modules: list[str] = []
        if isinstance(imp, ast.Import):
            modules = [alias.name for alias in imp.names]
        elif isinstance(imp, ast.ImportFrom) and imp.module:
            modules = [imp.module]

        for mod in modules:
            if "providence_runtime" in mod and mod != f"providence_runtime.{file_name}":
                circular.append(mod)

    return circular


def find_long_functions(
    functions: list[ast.FunctionDef], max_function_lines: int
) -> list[dict[str, Any]]:
    """Find functions exceeding `max_function_lines`, longest first."""
    long_funcs = []
    for func in functions:
        func_lines = (func.end_lineno or func.lineno) - func.lineno + 1
        if func_lines > max_function_lines:
            long_funcs.append(
                {"name": func.name, "lines": func_lines, "params": len(func.args.args)}
            )
    return sorted(long_funcs, key=lambda x: x["lines"], reverse=True)


def find_hardcoded_values(content: str) -> list[str]:
    """Find magic numbers, repeated string literals, and hardcoded URLs."""
    hardcoded: list[str] = []

    magic_numbers = re.findall(r"\b\d{3,}\b", content)
    if magic_numbers:
        hardcoded.extend(f"magic_number: {n}" for n in sorted(set(magic_numbers))[:5])

    string_literals = re.findall(r'"([^"]{10,})"', content)
    for s in string_literals:
        if string_literals.count(s) > 1:
            hardcoded.append(f"repeated_string: {s[:30]}...")
            break

    if "http://" in content or "https://" in content:
        hardcoded.append("hardcoded_urls")

    return hardcoded[:10]


# --- pattern registration -------------------------------------------------------


def _has_duplicate_imports(content: str) -> bool:
    lines = content.split("\n")
    import_lines = [
        ln for ln in lines if ln.strip().startswith("import") or "from" in ln
    ]
    return len(import_lines) > len(set(import_lines))


def _has_multiple_conditionals(content: str) -> bool:
    if_blocks = len(re.findall(r"if .+:", content))
    elif_blocks = len(re.findall(r"elif .+:", content))
    return if_blocks > 5 or elif_blocks > 3


def register_runtime_patterns() -> None:
    """Register the runtime analyzer's standardization patterns (idempotent)."""
    registry = PatternRegistry()
    registry.register(
        "duplicate_imports",
        Pattern("duplicate_imports", PatternType.HEURISTIC, _has_duplicate_imports),
        group="standardization",
    )
    registry.register(
        "multiple_conditionals",
        Pattern(
            "multiple_conditionals", PatternType.HEURISTIC, _has_multiple_conditionals
        ),
        group="standardization",
    )


# --- dimensions: refactoring -----------------------------------------------------


def _refactoring_detector(
    metrics: FileMetrics, content: str, config: AnalysisConfig
) -> DimensionResult:
    max_file_lines = config.refactoring.max_file_lines
    long_functions: list[dict[str, Any]] = metrics.custom_metrics.get(
        "long_functions", []
    )

    findings: list[str] = []
    if metrics.lines > max_file_lines:
        findings.append(f"File too long ({metrics.lines} lines)")
    for func in long_functions:
        findings.append(f"Function '{func['name']}' too long ({func['lines']} lines)")

    score = 100.0
    if metrics.lines > max_file_lines:
        score -= min(30.0, (metrics.lines - max_file_lines) / 20)
    if metrics.classes == 0 and metrics.lines > 100:
        score -= 10
    if metrics.functions > 10:
        score -= min(15.0, (metrics.functions - 10) / 5)
    if long_functions:
        score -= min(20.0, len(long_functions) * 5)

    return DimensionResult(
        name="refactoring",
        findings=findings,
        score=max(0.0, score),
        metadata={"long_functions": long_functions},
    )


def _refactoring_reporter(result: DimensionResult, template: ReportTemplate) -> str:
    body = (
        template.bullet_list(result.findings)
        if result.findings
        else "No refactoring issues found."
    )
    return template.section(
        f"Refactoring (score: {result.score:.0f}/100)", body, level=4
    )


# --- dimensions: performance ------------------------------------------------------


def _performance_detector(
    metrics: FileMetrics, content: str, config: AnalysisConfig
) -> DimensionResult:
    heavy_imports: list[str] = metrics.custom_metrics.get("heavy_imports", [])
    circular_deps: list[str] = metrics.custom_metrics.get("circular_deps", [])

    findings = [f"Heavy import: {name}" for name in heavy_imports]
    findings += [f"Circular dependency: {dep}" for dep in circular_deps]

    score = 100.0 - min(40, len(heavy_imports) * 10) - min(40, len(circular_deps) * 15)

    return DimensionResult(
        name="performance",
        findings=findings,
        score=max(0.0, score),
        metadata={"heavy_imports": heavy_imports, "circular_deps": circular_deps},
    )


def _performance_reporter(result: DimensionResult, template: ReportTemplate) -> str:
    body = (
        template.bullet_list(result.findings)
        if result.findings
        else "No performance issues found."
    )
    return template.section(
        f"Performance (score: {result.score:.0f}/100)", body, level=4
    )


# --- dimensions: standardization ---------------------------------------------------


def _standardization_detector(
    metrics: FileMetrics, content: str, config: AnalysisConfig
) -> DimensionResult:
    hardcoded_values: list[str] = metrics.custom_metrics.get("hardcoded_values", [])
    duplicate_patterns: list[str] = metrics.custom_metrics.get("duplicate_patterns", [])

    findings = [*hardcoded_values, *duplicate_patterns]

    score = (
        100.0 - min(50, len(hardcoded_values) * 5) - (10 if duplicate_patterns else 0)
    )

    return DimensionResult(
        name="standardization",
        findings=findings,
        score=max(0.0, score),
        metadata={
            "hardcoded_values": hardcoded_values,
            "duplicate_patterns": duplicate_patterns,
        },
    )


def _standardization_reporter(result: DimensionResult, template: ReportTemplate) -> str:
    body = (
        template.bullet_list(result.findings)
        if result.findings
        else "No standardization issues found."
    )
    return template.section(
        f"Standardization (score: {result.score:.0f}/100)", body, level=4
    )


# --- analyzer ------------------------------------------------------------------------


class RuntimeAnalyzer(GuardrailAnalyzer):
    """Analyzes the providence_runtime package across three quality dimensions."""

    def __init__(
        self,
        config: AnalysisConfig,
        output_dir: Path | None = None,
        target_dir: Path | None = None,
    ) -> None:
        register_runtime_patterns()
        self._target_dir = target_dir or (
            detect_repo_root()
            / "packages"
            / "core"
            / "providence_runtime"
            / "src"
            / "providence_runtime"
        )
        super().__init__(config, output_dir)

    def get_target_directory(self) -> Path:
        return self._target_dir

    def get_analysis_name(self) -> str:
        return "providence_runtime"

    def get_dimensions(self) -> list[AnalysisDimension]:
        return [
            AnalysisDimension(
                "refactoring",
                _refactoring_detector,
                _refactoring_reporter,
                description="Files/functions that are too large to maintain easily.",
                icon="\U0001f527",
            ),
            AnalysisDimension(
                "performance",
                _performance_detector,
                _performance_reporter,
                description="Heavy imports and potential circular dependencies.",
                icon="⚡",
            ),
            AnalysisDimension(
                "standardization",
                _standardization_detector,
                _standardization_reporter,
                description="Hardcoded values and duplicated patterns.",
                icon="\U0001f4d0",
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

        metrics.custom_metrics["long_functions"] = find_long_functions(
            functions, self.config.refactoring.max_function_lines
        )
        metrics.custom_metrics["heavy_imports"] = find_heavy_imports(imports)
        metrics.custom_metrics["circular_deps"] = find_circular_deps(file_path, imports)
        metrics.custom_metrics["hardcoded_values"] = find_hardcoded_values(content)
        metrics.custom_metrics["duplicate_patterns"] = PatternRegistry().find_matches(
            content, group="standardization"
        )

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
                f"{dimension.icon} {dimension.name}: avg score "
                f"{dim_summary.get('avg_score', 0.0):.1f}/100, "
                f"{dim_summary.get('files_with_issues', 0)} file(s) with findings"
            )

        sections = [
            template.header("Providence Runtime Module - Discovery Report"),
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
        sections = [template.header("Providence Runtime Module - Detailed Analysis")]

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
                    f"{dimension.icon} {dimension.name.title()}", body, level=2
                )
            )

        return "\n\n".join(sections)

    def _render_recommendations(self) -> str:
        template = ReportTemplate()
        sections = [template.header("Providence Runtime Module - Recommendations")]

        for dimension in self.get_dimensions():
            files_with_findings = [
                f
                for f in self.files
                if dimension.name in f.dimension_results
                and f.dimension_results[dimension.name].findings
            ]
            worst = sorted(
                files_with_findings,
                key=lambda f: f.dimension_results[dimension.name].score,
            )[:5]

            items = [
                f"`{f.name}` (score {f.dimension_results[dimension.name].score:.0f}/100): "
                + "; ".join(f.dimension_results[dimension.name].findings)
                for f in worst
            ]
            body = template.bullet_list(items) if items else "No action needed."
            sections.append(
                template.section(
                    f"{dimension.icon} {dimension.name.title()}", body, level=2
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
