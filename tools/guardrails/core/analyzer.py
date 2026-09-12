"""GuardrailAnalyzer: the concrete analysis pipeline orchestrator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from providence_core.utils.text_io import read_text_utf8
from tools.guardrails.core.config import AnalysisConfig
from tools.guardrails.core.dimension import AnalysisDimension
from tools.guardrails.core.discovery import discover_files
from tools.guardrails.core.metrics import AnalysisResult, FileMetrics


class GuardrailAnalyzer(ABC):
    """Generic pipeline for analyzing files across multiple dimensions.

    Concrete pipeline (`analyze_all`):
    1. Discover files to analyze
    2. Read and parse each file
    3. Extract base metrics (FileMetrics)
    4. Run all dimensions on each file
    5. Aggregate results across files
    6. Generate reports (subclass responsibility)
    """

    def __init__(self, config: AnalysisConfig, output_dir: Path | None = None) -> None:
        self.config = config
        self.output_dir = output_dir or self._default_output_dir()
        self.files: list[FileMetrics] = []
        self.results: AnalysisResult | None = None

    @abstractmethod
    def get_target_directory(self) -> Path:
        """Return the directory to analyze."""

    @abstractmethod
    def get_analysis_name(self) -> str:
        """Return analyzer identifier (e.g., 'providence_runtime', 'providence_telemetry')."""

    @abstractmethod
    def get_dimensions(self) -> list[AnalysisDimension]:
        """Return list of dimensions to analyze across."""

    @abstractmethod
    def create_file_metrics(self, file_path: Path, content: str) -> FileMetrics:
        """Create file-specific metrics object."""

    @abstractmethod
    def _generate_reports(self) -> None:
        """Render and persist reports for `self.results`."""

    def _default_output_dir(self) -> Path:
        return Path(".analysis/pending") / self.get_analysis_name()

    def analyze_all(self) -> AnalysisResult:
        """Run the full analysis pipeline and return the aggregated result."""
        for file_path in discover_files(self.get_target_directory(), self.config):
            content = read_text_utf8(file_path)
            metrics = self.create_file_metrics(file_path, content)

            for dimension in self.get_dimensions():
                metrics.dimension_results[dimension.name] = dimension.detect(
                    metrics, content, self.config
                )

            self.files.append(metrics)

        self.results = self._aggregate_results()
        self._generate_reports()
        return self.results

    def _aggregate_results(self) -> AnalysisResult:
        summary: dict[str, object] = {"total_files": len(self.files)}

        dimension_names = {
            name for file in self.files for name in file.dimension_results
        }
        for name in dimension_names:
            results = [
                file.dimension_results[name]
                for file in self.files
                if name in file.dimension_results
            ]
            scores = [result.score for result in results]
            summary[name] = {
                "avg_score": sum(scores) / len(scores) if scores else 0.0,
                "files_with_issues": sum(1 for r in results if r.findings),
                "total_findings": sum(len(r.findings) for r in results),
            }

        return AnalysisResult(
            analyzer_name=self.get_analysis_name(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            files=self.files,
            summary=summary,
        )
