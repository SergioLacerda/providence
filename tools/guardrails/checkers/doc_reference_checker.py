"""DocReferenceChecker: Phase 4a guardrail — docs/ -> packages/core + tools/sdd-compile.

Scans `docs/**/*.md` for backtick-quoted path references into `packages/core/` and
`tools/sdd-compile/`, flagging references whose target no longer exists on disk.
Read-only: this checker never writes to `docs/`, `packages/core/`, or
`tools/sdd-compile/` — only to its own report output directory.

See `.analysis/done/guardrails-framework-evaluation/guardrails-framework-design.md`,
"Phase 4 — Designed (Redirected 2026-07-24)" for the design (D1-D5) this implements.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from providence_core.utils.text_io import write_json_utf8, write_text_utf8
from tools.guardrails.core.analyzer import GuardrailAnalyzer
from tools.guardrails.core.config import AnalysisConfig
from tools.guardrails.core.dimension import AnalysisDimension
from tools.guardrails.core.metrics import DimensionResult, FileMetrics
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


# Backtick-quoted paths into the two primary docs/ consumers (D1: separate dimension,
# not the Python-AST detector helpers Phases 2-3 built). Restricting to backtick code
# spans is a deliberate precision choice (see design doc § Uncertainties): a bare-prose
# mention of "the packages/core directory" isn't flagged, only an exact quoted path.
REFERENCE_PATTERN = re.compile(r"`((?:packages/core|tools/sdd-compile)/[^`\s]+)`")

# Trailing `:123` or `:123-456` line-range suffixes (as used throughout this repo's own
# docs, e.g. `` `Makefile:180-193` ``) are not part of the filesystem path.
LINE_SUFFIX_PATTERN = re.compile(r":\d+(-\d+)?$")


@dataclass(frozen=True)
class CodeReference:
    """One backtick-quoted code-path reference found in a doc file."""

    text: str
    """The raw matched reference, including any trailing `:LINE` suffix."""
    line: int
    """1-based line number in the source doc file where the reference appears."""
    resolved_path: str
    """The reference with any trailing `:LINE` suffix stripped."""
    exists: bool
    """Whether `resolved_path` exists on disk, relative to the repo root."""


def _strip_line_suffix(reference: str) -> str:
    return LINE_SUFFIX_PATTERN.sub("", reference)


def find_code_references(content: str, repo_root: Path) -> list[CodeReference]:
    """Find backtick-quoted `packages/core/`/`tools/sdd-compile/` references.

    Each match is resolved relative to `repo_root` and checked for existence.
    Results are returned in document order.
    """
    references: list[CodeReference] = []
    for match in REFERENCE_PATTERN.finditer(content):
        raw = match.group(1)
        resolved = _strip_line_suffix(raw)
        line = content.count("\n", 0, match.start()) + 1
        exists = (repo_root / resolved).exists()
        references.append(
            CodeReference(text=raw, line=line, resolved_path=resolved, exists=exists)
        )
    return references


def _doc_references_detector(
    metrics: FileMetrics, content: str, config: AnalysisConfig
) -> DimensionResult:
    references: list[CodeReference] = metrics.custom_metrics.get("references", [])
    broken = [ref for ref in references if not ref.exists]

    findings = [
        f"{metrics.path}:{ref.line} -> `{ref.text}` (target does not exist)"
        for ref in broken
    ]

    score = 100.0 if not references else 100.0 * (1 - len(broken) / len(references))

    return DimensionResult(
        name="doc_code_references",
        findings=findings,
        score=max(0.0, score),
        metadata={
            "total_references": len(references),
            "broken_references": len(broken),
        },
    )


def _doc_references_reporter(result: DimensionResult, template: ReportTemplate) -> str:
    body = (
        template.bullet_list(result.findings)
        if result.findings
        else "No broken references found."
    )
    return template.section(
        f"Doc/Code References (score: {result.score:.0f}/100)", body, level=4
    )


class DocReferenceChecker(GuardrailAnalyzer):
    """Scans `docs/` for stale references into `packages/core`/`tools/sdd-compile`."""

    def __init__(
        self,
        config: AnalysisConfig,
        output_dir: Path | None = None,
        target_dir: Path | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self._repo_root = repo_root or detect_repo_root()
        self._target_dir = target_dir or (self._repo_root / "docs")
        super().__init__(config, output_dir)

    def get_target_directory(self) -> Path:
        return self._target_dir

    def get_analysis_name(self) -> str:
        return "doc_references"

    def get_dimensions(self) -> list[AnalysisDimension]:
        return [
            AnalysisDimension(
                "doc_code_references",
                _doc_references_detector,
                _doc_references_reporter,
                description=(
                    "Backtick-quoted docs/ references into packages/core or "
                    "tools/sdd-compile whose target no longer exists."
                ),
                icon="\U0001f517",
            )
        ]

    def create_file_metrics(self, file_path: Path, content: str) -> FileMetrics:
        references = find_code_references(content, self._repo_root)
        metrics = FileMetrics(
            name=file_path.name,
            path=file_path.relative_to(self._repo_root).as_posix()
            if file_path.is_absolute()
            else file_path.as_posix(),
            lines=len(content.splitlines()),
            classes=0,
            functions=0,
            imports=0,
        )
        metrics.custom_metrics["references"] = references
        return metrics

    def _generate_reports(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        write_text_utf8(self.output_dir / "discovery.md", self._render_discovery())
        write_text_utf8(self.output_dir / "analysis.md", self._render_analysis())
        write_text_utf8(
            self.output_dir / "recommendations.md", self._render_recommendations()
        )
        write_json_utf8(self.output_dir / "analysis.json", self._build_raw_data())

    def _files_with_broken_refs(self) -> list[FileMetrics]:
        return [
            f
            for f in self.files
            if any(not ref.exists for ref in f.custom_metrics.get("references", []))
        ]

    def _render_discovery(self) -> str:
        assert self.results is not None
        template = ReportTemplate()
        summary = self.results.summary
        dim_summary = summary.get("doc_code_references", {})

        total_refs = sum(
            len(f.custom_metrics.get("references", [])) for f in self.files
        )
        broken_files = self._files_with_broken_refs()

        summary_items = [
            f"Total doc files scanned: {summary['total_files']}",
            f"Total code references found: {total_refs}",
            f"\U0001f517 doc_code_references: avg score "
            f"{dim_summary.get('avg_score', 0.0):.1f}/100, "
            f"{len(broken_files)} file(s) with broken references",
        ]

        sections = [
            template.header("Doc Reference Checker - Discovery Report"),
            f"**Timestamp**: {self.results.timestamp}",
            template.section("Executive Summary", template.bullet_list(summary_items)),
        ]

        if broken_files:
            headers = ["File", "Broken", "Total"]
            rows = [
                [
                    f.path,
                    str(
                        sum(
                            1
                            for ref in f.custom_metrics.get("references", [])
                            if not ref.exists
                        )
                    ),
                    str(len(f.custom_metrics.get("references", []))),
                ]
                for f in sorted(
                    broken_files,
                    key=lambda fm: sum(
                        1
                        for r in fm.custom_metrics.get("references", [])
                        if not r.exists
                    ),
                    reverse=True,
                )
            ]
            sections.append(
                template.section(
                    "Files With Broken References", template.table(headers, rows)
                )
            )

        return "\n\n".join(sections)

    def _render_analysis(self) -> str:
        template = ReportTemplate()
        sections = [template.header("Doc Reference Checker - Detailed Analysis")]

        dimension = self.get_dimensions()[0]
        file_sections = []
        for file in self.files:
            result = file.dimension_results.get(dimension.name)
            if result and result.findings:
                file_sections.append(
                    f"**`{file.path}`**\n\n" + dimension.report(result, template)
                )

        body = "\n\n".join(file_sections) if file_sections else "No findings."
        sections.append(
            template.section(f"{dimension.icon} {dimension.name}", body, level=2)
        )

        return "\n\n".join(sections)

    def _render_recommendations(self) -> str:
        template = ReportTemplate()
        sections = [template.header("Doc Reference Checker - Recommendations")]

        broken_files = self._files_with_broken_refs()
        if not broken_files:
            sections.append(
                template.section(
                    "Action Items", "No action needed — no broken references found."
                )
            )
            return "\n\n".join(sections)

        items = [
            f"`{f.path}`: "
            + "; ".join(
                f"`{ref.text}`"
                for ref in f.custom_metrics.get("references", [])
                if not ref.exists
            )
            for f in broken_files
        ]
        sections.append(
            template.section(
                "Action Items — Fix or Remove Stale References",
                template.bullet_list(items),
            )
        )

        return "\n\n".join(sections)

    def _build_raw_data(self) -> dict[str, Any]:
        assert self.results is not None
        return {
            "analyzer_name": self.results.analyzer_name,
            "timestamp": self.results.timestamp,
            "files": [
                {
                    **{
                        k: v
                        for k, v in asdict(f).items()
                        if k not in ("dimension_results", "custom_metrics")
                    },
                    "references": [
                        asdict(ref) for ref in f.custom_metrics.get("references", [])
                    ],
                    "dimension_results": {
                        name: asdict(result)
                        for name, result in f.dimension_results.items()
                    },
                }
                for f in self.files
            ],
            "summary": self.results.summary,
        }
