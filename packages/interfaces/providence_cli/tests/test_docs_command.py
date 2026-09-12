"""Tests for providence_cli.commands.docs  deploy command coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()
pytestmark = pytest.mark.unit


class TestDocsDeploy:
    def test_no_mkdocs_config_skips(self) -> None:
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 0
        assert "Skipping docs deploy" in result.output

    def test_mkdocs_yaml_also_accepted(self) -> None:
        with runner.isolated_filesystem():
            Path("mkdocs.yaml").write_text("", encoding="utf-8")
            with patch("shutil.which", return_value=None):
                result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 1
        assert "mkdocs command not found" in result.output

    def test_mkdocs_not_in_path_exits_1(self) -> None:
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with patch("shutil.which", return_value=None):
                result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 1
        assert "mkdocs command not found" in result.output

    def test_deploy_success_with_force(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with (
                patch("shutil.which", return_value="/usr/bin/mkdocs"),
                patch(
                    "providence_core.utils.process.SafeProcessRunner",
                    return_value=mock_runner,
                ),
            ):
                result = runner.invoke(app, ["docs", "deploy", "--force"])
        assert result.exit_code == 0
        called_cmd = mock_runner.run.call_args[0][0]
        assert "--force" in called_cmd

    def test_deploy_success_without_force(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with (
                patch("shutil.which", return_value="/usr/bin/mkdocs"),
                patch(
                    "providence_core.utils.process.SafeProcessRunner",
                    return_value=mock_runner,
                ),
            ):
                result = runner.invoke(app, ["docs", "deploy", "--no-force"])
        assert result.exit_code == 0
        called_cmd = mock_runner.run.call_args[0][0]
        assert "--force" not in called_cmd

    def test_non_zero_exit_error_exits_1(self) -> None:
        from providence_core.utils.process import ProcessNonZeroExitError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessNonZeroExitError("mkdocs failed")
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with (
                patch("shutil.which", return_value="/usr/bin/mkdocs"),
                patch(
                    "providence_core.utils.process.SafeProcessRunner",
                    return_value=mock_runner,
                ),
            ):
                result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 1
        assert "docs deploy failed" in result.output

    def test_authorization_error_exits_2(self) -> None:
        from providence_core.utils.process import ProcessAuthorizationError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessAuthorizationError("blocked")
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with (
                patch("shutil.which", return_value="/usr/bin/mkdocs"),
                patch(
                    "providence_core.utils.process.SafeProcessRunner",
                    return_value=mock_runner,
                ),
            ):
                result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 2
        assert "blocked by policy" in result.output

    def test_timeout_error_exits_124(self) -> None:
        from providence_core.utils.process import ProcessTimeoutError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessTimeoutError(["mkdocs", "gh-deploy"], 30.0)
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with (
                patch("shutil.which", return_value="/usr/bin/mkdocs"),
                patch(
                    "providence_core.utils.process.SafeProcessRunner",
                    return_value=mock_runner,
                ),
            ):
                result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 124
        assert "timed out" in result.output

    def test_spawn_error_exits_127(self) -> None:
        from providence_core.utils.process import ProcessSpawnError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessSpawnError("cannot spawn")
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with (
                patch("shutil.which", return_value="/usr/bin/mkdocs"),
                patch(
                    "providence_core.utils.process.SafeProcessRunner",
                    return_value=mock_runner,
                ),
            ):
                result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 127
        assert "could not start" in result.output


class TestDocsGovernanceSources:
    def test_validate_governance_sources_success(self) -> None:
        with (
            runner.isolated_filesystem(),
            patch(
                "providence_cli.commands.docs.validate_governance_sources",
                return_value=MagicMock(
                    ok=True,
                    errors=[],
                    warnings=[],
                    mandate_ids=["M001"],
                    guideline_ids=["G01"],
                    handbook_ids=["HBK"],
                ),
            ),
        ):
            result = runner.invoke(app, ["docs", "validate-governance-sources"])
        assert result.exit_code == 0
        assert "docs governance sources validated" in result.output

    def test_validate_governance_sources_failure(self) -> None:
        with (
            runner.isolated_filesystem(),
            patch(
                "providence_cli.commands.docs.validate_governance_sources",
                return_value=MagicMock(
                    ok=False,
                    errors=["duplicate active mandate id M001"],
                    warnings=[],
                    mandate_ids=[],
                    guideline_ids=[],
                    handbook_ids=[],
                ),
            ),
        ):
            result = runner.invoke(app, ["docs", "validate-governance-sources"])
        assert result.exit_code == 1
        assert "duplicate active mandate id M001" in result.output

    def test_generate_handbook_success(self) -> None:
        with (
            runner.isolated_filesystem(),
            patch(
                "providence_cli.commands.docs.validate_governance_sources",
                return_value=MagicMock(
                    ok=True,
                    errors=[],
                    warnings=[],
                    mandate_ids=[],
                    guideline_ids=[],
                    handbook_ids=["HBK"],
                ),
            ),
            patch(
                "providence_cli.commands.docs.generate_runtime_handbook",
                return_value=[Path.cwd() / ".providence/source/handbook/index.yaml"],
            ),
        ):
            result = runner.invoke(app, ["docs", "generate-handbook"])
        assert result.exit_code == 0
        assert "runtime handbook generated" in result.output

    def test_lookup_handbook_success(self) -> None:
        with (
            runner.isolated_filesystem(),
            patch(
                "providence_cli.commands.docs.lookup_runtime_handbook",
                return_value=MagicMock(
                    status="matched",
                    diagnostic="handbook_match=1",
                    matches=[
                        {
                            "id": "HBK",
                            "source_doc": "docs/a.md",
                            "runtime_doc": ".providence/source/handbook/a.yaml",
                        }
                    ],
                ),
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "docs",
                    "lookup-handbook",
                    "--task-type",
                    "planning",
                    "--mandate-ref",
                    "M003",
                    "--operation-phase",
                    "context_loading",
                ],
            )
        assert result.exit_code == 0
        assert "runtime handbook lookup: handbook_match=1" in result.output
        assert "HBK source=docs/a.md" in result.output

    def test_lookup_handbook_missing_exits_1(self) -> None:
        with (
            runner.isolated_filesystem(),
            patch(
                "providence_cli.commands.docs.lookup_runtime_handbook",
                return_value=MagicMock(
                    status="missing",
                    diagnostic="handbook_index_missing",
                    matches=[],
                ),
            ),
        ):
            result = runner.invoke(app, ["docs", "lookup-handbook"])
        assert result.exit_code == 1
        assert "handbook_index_missing" in result.output
