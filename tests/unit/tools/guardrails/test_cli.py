"""Unit tests for tools.guardrails.cli."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.guardrails.checkers.doc_reference_checker import DocReferenceChecker
from tools.guardrails.cli import (
    ANALYZERS,
    DEFAULT_CONFIG_PATH,
    _config_for,
    build_parser,
    main,
    run,
)
from tools.guardrails.core.config import AnalysisConfig
from tools.guardrails.core.patterns import PatternRegistry

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_pattern_registry():
    PatternRegistry._instance = None
    yield
    PatternRegistry._instance = None


class TestBuildParser:
    """build_parser exposes the expected CLI options and defaults."""

    def test_defaults(self) -> None:
        args = build_parser().parse_args([])

        assert args.analyzer == "all"
        assert args.config == DEFAULT_CONFIG_PATH
        assert args.output_dir is None
        assert args.target_dir is None

    def test_explicit_analyzer(self) -> None:
        args = build_parser().parse_args(["--analyzer", "runtime"])

        assert args.analyzer == "runtime"

    def test_invalid_analyzer_rejected(self) -> None:
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--analyzer", "bogus"])

    def test_doc_references_is_a_valid_analyzer_choice(self) -> None:
        args = build_parser().parse_args(["--analyzer", "doc_references"])
        assert args.analyzer == "doc_references"


class TestAnalyzerRegistry:
    """doc_references is wired into ANALYZERS with a Markdown config override."""

    def test_doc_references_registered(self) -> None:
        assert ANALYZERS["doc_references"] is DocReferenceChecker

    def test_config_override_applies_markdown_glob(self) -> None:
        config = _config_for("doc_references", AnalysisConfig())
        assert config.include_patterns == ["**/*.md"]

    def test_config_override_is_noop_for_other_analyzers(self) -> None:
        config = AnalysisConfig()
        assert _config_for("runtime", config) is config


@pytest.fixture
def project(tmp_path: Path) -> Path:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "module.py").write_text(
        "import pandas as pd\n\n\ndef process_event():\n    return pd.DataFrame()\n",
        encoding="utf-8",
    )
    return pkg


class TestRun:
    """run() instantiates the requested analyzer and writes its reports."""

    def test_runtime_writes_reports(self, project: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"

        run("runtime", AnalysisConfig(), output_dir=out, target_dir=project)

        assert (out / "discovery.md").exists()
        assert (out / "analysis.md").exists()
        assert (out / "recommendations.md").exists()
        assert (out / "analysis.json").exists()

    def test_telemetry_writes_reports(self, project: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"

        run("telemetry", AnalysisConfig(), output_dir=out, target_dir=project)

        data = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
        assert data["analyzer_name"] == "providence_telemetry"


class TestMainEndToEnd:
    """main() dispatches to one or all analyzers, writing per-analyzer output dirs."""

    def test_single_analyzer(self, project: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"

        exit_code = main(
            [
                "--analyzer",
                "runtime",
                "--target-dir",
                str(project),
                "--output-dir",
                str(out),
            ]
        )

        assert exit_code == 0
        assert (out / "discovery.md").exists()

    def test_all_analyzers_use_per_analyzer_subdirs(
        self, project: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "out"

        exit_code = main(
            [
                "--analyzer",
                "all",
                "--target-dir",
                str(project),
                "--output-dir",
                str(out),
            ]
        )

        assert exit_code == 0
        assert (out / "runtime" / "analysis.json").exists()
        assert (out / "telemetry" / "analysis.json").exists()


class TestConfigLoading:
    """main() wires --config through to AnalysisConfig.load_yaml."""

    def test_custom_config_overrides_thresholds(
        self, project: Path, tmp_path: Path
    ) -> None:
        config_path = tmp_path / "custom.yaml"
        config_path.write_text(
            "analysis:\n  refactoring:\n    max_file_lines: 1\n",
            encoding="utf-8",
        )
        out = tmp_path / "out"

        main(
            [
                "--analyzer",
                "runtime",
                "--config",
                str(config_path),
                "--target-dir",
                str(project),
                "--output-dir",
                str(out),
            ]
        )

        analysis = (out / "analysis.md").read_text(encoding="utf-8")
        assert "File too long" in analysis
