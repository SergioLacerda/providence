"""Tests for source writers and directory utilities  Phase 5 generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from providence_core.utils.text_io import read_text_utf8
from providence_wizard.orchestration.phase_4_5_6_generator import (
    Phase456Generator,
    _create_source_directories,
    _generate_plugin_workspace_dirs,
)
from providence_wizard.orchestration.writers.guidelines_writer import GuidelinesWriter
from providence_wizard.orchestration.writers.mandates_writer import MandatesWriter
from providence_wizard.orchestration.writers.readme_writer import ReadmeWriter

_SAMPLE_MANDATES = [
    {
        "id": "M001",
        "title": "Validate First",
        "criticality": "MANDATORY",
        "content": "Always validate.",
    },
    {
        "id": "M002",
        "title": None,
        "criticality": "MANDATORY",
        "description": "Use descriptions.",
        "summary_minimal": None,
    },
    {"id": "M003", "title": "No Desc", "criticality": "MANDATORY"},
]

_SAMPLE_GUIDELINES: dict[str, Any] = {
    "G001": {
        "id": "G001",
        "title": "Test Coverage",
        "type": "GUIDELINE",
        "status": "required",
        "customizable": True,
        "content": "Write tests.",
    },
    "G002": {
        "id": "G002",
        "title": None,
        "type": "GUIDELINE",
        "status": "optional",
        "customizable": False,
        "content": "",
    },
}

_SAMPLE_BY_CATEGORY = {
    "testing": [
        {
            "id": "G001",
            "title": "Test Coverage",
            "type": "GUIDELINE",
            "status": "required",
            "customizable": True,
            "content": "Write tests.",
        },
    ],
    "custom_cat": [
        {
            "id": "G002",
            "title": "Custom",
            "type": "GUIDELINE",
            "status": "optional",
            "customizable": True,
            "content": "Custom content.",
        },
    ],
}

_CONFIG = {
    "language": "Python",
    "adoption_level": "FULL",
    "locale": "en",
    "docs_language": "English",
    "docs_locale": "en",
    "language_context": {
        "preferred_human_language": "English",
        "preferred_chat_language": "English",
        "preferred_ui_language": "English",
        "preferred_local_docs_language": "English",
    },
}


def _dirs(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    output_base = tmp_path / "out"
    source_dir = output_base / ".providence" / "source"
    return (
        output_base,
        source_dir,
        source_dir / "mandates",
        source_dir / "guidelines",
        output_base / ".providence" / "runtime",
    )


def _setup_dirs(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    output_base, source_dir, mandates_dir, guidelines_dir, runtime_dir = _dirs(tmp_path)
    _create_source_directories(output_base, mandates_dir, guidelines_dir, runtime_dir)
    return output_base, source_dir, mandates_dir, guidelines_dir, runtime_dir


def _make_generator(tmp_path: Path, verbose: bool = False) -> Phase456Generator:
    fake_paths = {
        "root": tmp_path,
        "client_compiled": tmp_path / "build",
    }
    with patch(
        "providence_wizard.orchestration.phase_4_5_6_generator.get_sdd_paths",
        return_value=fake_paths,
    ):
        return Phase456Generator(
            repo_root=tmp_path,
            output_base=tmp_path / "out",
            config=_CONFIG,
            verbose=verbose,
        )


class TestWriteSourcesIsolationGuard:
    def test_test_output_dir_not_set_allows_write_sources(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_TEST_OUTPUT_DIR", raising=False)
        gen = _make_generator(tmp_path)
        result: dict[str, Any] = {"errors": []}
        # Mock writers so _write_sources doesn't need real governance files
        with (
            patch.object(MandatesWriter, "generate", return_value=True),
            patch.object(GuidelinesWriter, "generate", return_value=True),
            patch.object(ReadmeWriter, "generate_source_readme", return_value=True),
            patch.object(ReadmeWriter, "generate_runtime_readme", return_value=True),
            patch(
                "providence_wizard.orchestration.phase_4_5_6_generator._create_source_directories",
                return_value=True,
            ),
            patch(
                "providence_wizard.orchestration.phase_4_5_6_generator._generate_plugin_workspace_dirs",
                return_value=True,
            ),
        ):
            assert gen._write_sources([], {}, {}, result) is True

    def test_test_output_dir_set_not_repo_root_allows_write_sources(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "true")
        gen = _make_generator(tmp_path)
        result: dict[str, Any] = {"errors": []}
        with (
            patch("providence_core.utils.environment.is_repo_root", return_value=False),
            patch.object(MandatesWriter, "generate", return_value=True),
            patch.object(GuidelinesWriter, "generate", return_value=True),
            patch.object(ReadmeWriter, "generate_source_readme", return_value=True),
            patch.object(ReadmeWriter, "generate_runtime_readme", return_value=True),
            patch(
                "providence_wizard.orchestration.phase_4_5_6_generator._create_source_directories",
                return_value=True,
            ),
            patch(
                "providence_wizard.orchestration.phase_4_5_6_generator._generate_plugin_workspace_dirs",
                return_value=True,
            ),
        ):
            assert gen._write_sources([], {}, {}, result) is True

    def test_test_output_dir_set_repo_root_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "true")
        gen = _make_generator(tmp_path)
        result: dict[str, Any] = {"errors": []}
        with patch("providence_core.utils.environment.is_repo_root", return_value=True):
            assert gen._write_sources([], {}, {}, result) is False
        assert any("SDD_ISOLATION_ERROR" in e for e in result["errors"])

    def test_oserror_in_is_repo_root_does_not_block(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "true")
        gen = _make_generator(tmp_path)
        result: dict[str, Any] = {"errors": []}
        with (
            patch(
                "providence_core.utils.environment.is_repo_root",
                side_effect=OSError("disk error"),
            ),
            patch.object(MandatesWriter, "generate", return_value=True),
            patch.object(GuidelinesWriter, "generate", return_value=True),
            patch.object(ReadmeWriter, "generate_source_readme", return_value=True),
            patch.object(ReadmeWriter, "generate_runtime_readme", return_value=True),
            patch(
                "providence_wizard.orchestration.phase_4_5_6_generator._create_source_directories",
                return_value=True,
            ),
            patch(
                "providence_wizard.orchestration.phase_4_5_6_generator._generate_plugin_workspace_dirs",
                return_value=True,
            ),
        ):
            assert gen._write_sources([], {}, {}, result) is True

    def test_valueerror_in_is_repo_root_does_not_block(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "true")
        gen = _make_generator(tmp_path)
        result: dict[str, Any] = {"errors": []}
        with (
            patch(
                "providence_core.utils.environment.is_repo_root",
                side_effect=ValueError("bad path"),
            ),
            patch.object(MandatesWriter, "generate", return_value=True),
            patch.object(GuidelinesWriter, "generate", return_value=True),
            patch.object(ReadmeWriter, "generate_source_readme", return_value=True),
            patch.object(ReadmeWriter, "generate_runtime_readme", return_value=True),
            patch(
                "providence_wizard.orchestration.phase_4_5_6_generator._create_source_directories",
                return_value=True,
            ),
            patch(
                "providence_wizard.orchestration.phase_4_5_6_generator._generate_plugin_workspace_dirs",
                return_value=True,
            ),
        ):
            assert gen._write_sources([], {}, {}, result) is True


class TestCreateSourceDirectories:
    def test_creates_required_dirs(self, tmp_path: Path) -> None:
        output_base, _, mandates_dir, guidelines_dir, runtime_dir = _dirs(tmp_path)
        result = _create_source_directories(
            output_base, mandates_dir, guidelines_dir, runtime_dir
        )
        assert result is True
        assert mandates_dir.exists()
        assert runtime_dir.exists()
        assert (output_base / ".github" / "workflows").exists()

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        output_base, _, mandates_dir, guidelines_dir, runtime_dir = _dirs(tmp_path)
        with patch("pathlib.Path.mkdir", side_effect=OSError("no space")):
            result = _create_source_directories(
                output_base, mandates_dir, guidelines_dir, runtime_dir
            )
        assert result is False


class TestMandatesWriter:
    def test_creates_mandates_md(self, tmp_path: Path) -> None:
        output_base, _, mandates_dir, _, _ = _setup_dirs(tmp_path)
        writer = MandatesWriter(mandates_dir, list(_SAMPLE_MANDATES), _CONFIG)
        assert writer.generate() is True
        assert (mandates_dir / "mandates.md").exists()

    def test_content_includes_mandate_ids(self, tmp_path: Path) -> None:
        _, _, mandates_dir, _, _ = _setup_dirs(tmp_path)
        writer = MandatesWriter(mandates_dir, list(_SAMPLE_MANDATES), _CONFIG)
        writer.generate()
        content = read_text_utf8(mandates_dir / "mandates.md")
        assert "M001" in content
        assert "M002" in content

    def test_mandate_with_content_field(self, tmp_path: Path) -> None:
        _, _, mandates_dir, _, _ = _setup_dirs(tmp_path)
        mandates = [
            {"id": "M001", "title": "T", "criticality": "HIGH", "content": "my content"}
        ]
        writer = MandatesWriter(mandates_dir, mandates, _CONFIG)
        writer.generate()
        content = read_text_utf8(mandates_dir / "mandates.md")
        assert "my content" in content

    def test_mandate_with_description_fallback(self, tmp_path: Path) -> None:
        _, _, mandates_dir, _, _ = _setup_dirs(tmp_path)
        mandates = [
            {
                "id": "M001",
                "title": "T",
                "criticality": "HIGH",
                "description": "desc fallback",
            }
        ]
        writer = MandatesWriter(mandates_dir, mandates, _CONFIG)
        writer.generate()
        content = read_text_utf8(mandates_dir / "mandates.md")
        assert "desc fallback" in content

    def test_mandate_missing_criticality_defaults_to_mandatory(
        self, tmp_path: Path
    ) -> None:
        _, _, mandates_dir, _, _ = _setup_dirs(tmp_path)
        mandates = [{"id": "M001", "title": "T", "content": "my content"}]
        writer = MandatesWriter(mandates_dir, mandates, _CONFIG)
        writer.generate()
        content = read_text_utf8(mandates_dir / "mandates.md")
        assert "**Criticality**: MANDATORY" in content
        assert "OBRIGATRIO" not in content

    def test_m011_renders_language_policy_summary(self, tmp_path: Path) -> None:
        _, _, mandates_dir, _, _ = _setup_dirs(tmp_path)
        mandates = [
            {
                "id": "M011",
                "title": "English Language Standard",
                "criticality": "HIGH",
                "content": "English is mandatory for technical artifacts.",
            }
        ]
        writer = MandatesWriter(mandates_dir, mandates, _CONFIG)
        writer.generate()
        content = read_text_utf8(mandates_dir / "mandates.md")
        assert "Mandatory surfaces" in content
        assert "technical_docs" in content
        assert "Contextual surfaces" in content
        assert "workspace_local_docs" in content
        assert "Guideline anchors" in content

    def test_mandate_missing_title_uses_default(self, tmp_path: Path) -> None:
        _, _, mandates_dir, _, _ = _setup_dirs(tmp_path)
        writer = MandatesWriter(
            mandates_dir, [{"id": "M001", "criticality": "HIGH"}], _CONFIG
        )
        writer.generate()
        content = read_text_utf8(mandates_dir / "mandates.md")
        assert "Mandate M001" in content

    def test_empty_mandates_list(self, tmp_path: Path) -> None:
        _, _, mandates_dir, _, _ = _setup_dirs(tmp_path)
        writer = MandatesWriter(mandates_dir, [], _CONFIG)
        assert writer.generate() is True

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        _, _, mandates_dir, _, _ = _setup_dirs(tmp_path)
        writer = MandatesWriter(mandates_dir, list(_SAMPLE_MANDATES), _CONFIG)
        with patch("builtins.open", side_effect=OSError("disk full")):
            assert writer.generate() is False


class TestGuidelinesWriter:
    def test_creates_category_files(self, tmp_path: Path) -> None:
        _, _, _, guidelines_dir, _ = _setup_dirs(tmp_path)
        writer = GuidelinesWriter(guidelines_dir, dict(_SAMPLE_BY_CATEGORY))
        assert writer.generate() is True
        assert (guidelines_dir / "testing.md").exists()

    def test_known_category_uses_friendly_name(self, tmp_path: Path) -> None:
        _, _, _, guidelines_dir, _ = _setup_dirs(tmp_path)
        GuidelinesWriter(guidelines_dir, dict(_SAMPLE_BY_CATEGORY)).generate()
        content = read_text_utf8(guidelines_dir / "testing.md")
        assert "Testing" in content

    def test_unknown_category_uses_title_case(self, tmp_path: Path) -> None:
        _, _, _, guidelines_dir, _ = _setup_dirs(tmp_path)
        GuidelinesWriter(guidelines_dir, dict(_SAMPLE_BY_CATEGORY)).generate()
        content = read_text_utf8(guidelines_dir / "custom_cat.md")
        assert "Custom_Cat" in content

    def test_guideline_with_no_title_uses_default(self, tmp_path: Path) -> None:
        _, _, _, guidelines_dir, _ = _setup_dirs(tmp_path)
        by_cat = {
            "testing": [
                {
                    "id": "G001",
                    "content": "c",
                    "type": "T",
                    "status": "s",
                    "customizable": True,
                }
            ]
        }
        GuidelinesWriter(guidelines_dir, by_cat).generate()
        content = read_text_utf8(guidelines_dir / "testing.md")
        assert "Guideline G001" in content

    def test_guideline_not_customizable(self, tmp_path: Path) -> None:
        _, _, _, guidelines_dir, _ = _setup_dirs(tmp_path)
        by_cat = {
            "testing": [
                {
                    "id": "G001",
                    "title": "T",
                    "content": "c",
                    "type": "T",
                    "status": "s",
                    "customizable": False,
                }
            ]
        }
        GuidelinesWriter(guidelines_dir, by_cat).generate()
        content = read_text_utf8(guidelines_dir / "testing.md")
        assert "No" in content

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        _, _, _, guidelines_dir, _ = _setup_dirs(tmp_path)
        writer = GuidelinesWriter(guidelines_dir, dict(_SAMPLE_BY_CATEGORY))
        with patch("builtins.open", side_effect=OSError("disk full")):
            assert writer.generate() is False


class TestReadmeWriterSourceReadme:
    def _make_writer(self, source_dir: Path, runtime_dir: Path) -> ReadmeWriter:
        return ReadmeWriter(
            source_dir=source_dir,
            runtime_dir=runtime_dir,
            mandates=list(_SAMPLE_MANDATES),
            guidelines=dict(_SAMPLE_GUIDELINES),
            guidelines_by_category=dict(_SAMPLE_BY_CATEGORY),
            config=_CONFIG,
        )

    def test_creates_readme(self, tmp_path: Path) -> None:
        _, source_dir, _, _, runtime_dir = _setup_dirs(tmp_path)
        assert (
            self._make_writer(source_dir, runtime_dir).generate_source_readme() is True
        )
        assert (source_dir / "README.md").exists()

    def test_readme_contains_mandate_count(self, tmp_path: Path) -> None:
        _, source_dir, _, _, runtime_dir = _setup_dirs(tmp_path)
        self._make_writer(source_dir, runtime_dir).generate_source_readme()
        content = read_text_utf8(source_dir / "README.md")
        assert str(len(_SAMPLE_MANDATES)) in content

    def test_readme_contains_categories(self, tmp_path: Path) -> None:
        _, source_dir, _, _, runtime_dir = _setup_dirs(tmp_path)
        self._make_writer(source_dir, runtime_dir).generate_source_readme()
        content = read_text_utf8(source_dir / "README.md")
        assert "testing" in content.lower() or "Testing" in content

    def test_readme_contains_language_context(self, tmp_path: Path) -> None:
        _, source_dir, _, _, runtime_dir = _setup_dirs(tmp_path)
        self._make_writer(source_dir, runtime_dir).generate_source_readme()
        content = read_text_utf8(source_dir / "README.md")
        assert "Wizard Language Context" in content
        assert "Interaction locale: en" in content
        assert "Docs locale: en" in content
        assert "Local docs: English" in content
        assert "guidelines.dsl" in content
        assert ".analysis/" in content

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        _, source_dir, _, _, runtime_dir = _setup_dirs(tmp_path)
        with patch("builtins.open", side_effect=OSError("disk full")):
            assert (
                self._make_writer(source_dir, runtime_dir).generate_source_readme()
                is False
            )


class TestReadmeWriterRuntimeReadme:
    def _make_writer(self, source_dir: Path, runtime_dir: Path) -> ReadmeWriter:
        return ReadmeWriter(
            source_dir=source_dir,
            runtime_dir=runtime_dir,
            mandates=list(_SAMPLE_MANDATES),
            guidelines=dict(_SAMPLE_GUIDELINES),
            guidelines_by_category=dict(_SAMPLE_BY_CATEGORY),
            config=_CONFIG,
        )

    def test_creates_readme(self, tmp_path: Path) -> None:
        _, source_dir, _, _, runtime_dir = _setup_dirs(tmp_path)
        assert (
            self._make_writer(source_dir, runtime_dir).generate_runtime_readme() is True
        )
        assert (runtime_dir / "README.md").exists()

    def test_readme_has_pre_cache_content(self, tmp_path: Path) -> None:
        _, source_dir, _, _, runtime_dir = _setup_dirs(tmp_path)
        self._make_writer(source_dir, runtime_dir).generate_runtime_readme()
        content = read_text_utf8(runtime_dir / "README.md")
        assert "Pre-Cache" in content or "pre-cache" in content.lower()
        assert "Interaction locale: en" in content
        assert "Docs locale: en" in content

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        _, source_dir, _, _, runtime_dir = _setup_dirs(tmp_path)
        with patch("builtins.open", side_effect=OSError("disk full")):
            assert (
                self._make_writer(source_dir, runtime_dir).generate_runtime_readme()
                is False
            )


class TestGeneratePluginWorkspaceDirs:
    def test_success(self, tmp_path: Path) -> None:
        output_base, _, mandates_dir, guidelines_dir, runtime_dir = _setup_dirs(
            tmp_path
        )
        mock_plugins = MagicMock(return_value={"registry_path": "/fake/plugins.yaml"})
        mock_contracts = MagicMock(return_value={"files_written": 3})
        with (
            patch(
                "providence_cli.generators._plugins.generate_plugins_registry",
                mock_plugins,
            ),
            patch(
                "providence_cli.generators._contracts.generate_contracts",
                mock_contracts,
            ),
        ):
            assert _generate_plugin_workspace_dirs(output_base, _CONFIG) is True

    def test_creates_analysis_subdirs(self, tmp_path: Path) -> None:
        output_base, _, mandates_dir, guidelines_dir, runtime_dir = _setup_dirs(
            tmp_path
        )
        with (
            patch(
                "providence_cli.generators._plugins.generate_plugins_registry",
                return_value={},
            ),
            patch(
                "providence_cli.generators._contracts.generate_contracts",
                return_value={"files_written": 0},
            ),
        ):
            _generate_plugin_workspace_dirs(output_base, _CONFIG)
        for state in ("todo", "pending", "refined", "done"):
            assert (output_base / ".providence" / "analysis" / state).exists()

    def test_creates_docs_dir(self, tmp_path: Path) -> None:
        output_base, _, mandates_dir, guidelines_dir, runtime_dir = _setup_dirs(
            tmp_path
        )
        with (
            patch(
                "providence_cli.generators._plugins.generate_plugins_registry",
                return_value={},
            ),
            patch(
                "providence_cli.generators._contracts.generate_contracts",
                return_value={"files_written": 0},
            ),
        ):
            _generate_plugin_workspace_dirs(output_base, _CONFIG)
        assert (output_base / ".providence" / "docs").exists()

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        output_base, _, mandates_dir, guidelines_dir, runtime_dir = _setup_dirs(
            tmp_path
        )
        with patch(
            "providence_cli.generators._plugins.generate_plugins_registry",
            side_effect=RuntimeError("boom"),
        ):
            assert _generate_plugin_workspace_dirs(output_base, _CONFIG) is False
