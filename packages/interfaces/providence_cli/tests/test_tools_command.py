"""Tests for providence_cli.commands.tools  list and run command coverage."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from providence_cli.commands.tools import _find_repo_root
from providence_cli.main import app

runner = CliRunner()
pytestmark = pytest.mark.unit


def test_find_repo_root_delegates_to_detect(tmp_path: Path) -> None:
    with patch(
        "providence_cli.utils.environment.detect_repo_root", return_value=tmp_path
    ):
        assert _find_repo_root() == tmp_path


def _make_tools_dir(root: Path) -> Path:
    tools_dir = root / "tools"
    tools_dir.mkdir()
    return tools_dir


def _write_registry(tools_dir: Path, body: str) -> Path:
    registry = tools_dir / "registry.yaml"
    registry.write_text(body, encoding="utf-8")
    return registry


class TestToolsList:
    def test_tools_dir_not_found_exits_1(self, tmp_path: Path) -> None:
        with patch(
            "providence_cli.commands.tools._find_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 1
        assert "tools directory not found" in result.output

    def test_lists_python_scripts(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "health_check.py").write_text("", encoding="utf-8")
        with patch(
            "providence_cli.commands.tools._find_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 0
        assert "health_check.py" in result.output

    def test_skips_dunder_files(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "__init__.py").write_text("", encoding="utf-8")
        (tools_dir / "real_tool.py").write_text("", encoding="utf-8")
        with patch(
            "providence_cli.commands.tools._find_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 0
        assert "__init__.py" not in result.output
        assert "real_tool.py" in result.output

    def test_lists_nested_scripts(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        sub = tools_dir / "health"
        sub.mkdir()
        (sub / "check.py").write_text("", encoding="utf-8")
        with patch(
            "providence_cli.commands.tools._find_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 0
        assert "check.py" in result.output

    def test_manifest_default_lists_only_public_active_tools(
        self, tmp_path: Path
    ) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "public.py").write_text("", encoding="utf-8")
        (tools_dir / "internal.py").write_text("", encoding="utf-8")
        _write_registry(
            tools_dir,
            """
schema_version: "1"
tools:
  - id: public/check
    path: tools/public.py
    visibility: public
    status: active
    runner: uv-python
    description: Public check
  - id: internal/check
    path: tools/internal.py
    visibility: internal
    status: active
    runner: uv-python
    description: Internal check
""",
        )
        with patch(
            "providence_cli.commands.tools._find_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 0
        assert "public/check" in result.output
        assert "Public check" in result.output
        assert "internal/check" not in result.output

    def test_manifest_list_all_includes_internal_deprecated_and_projects(
        self, tmp_path: Path
    ) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        project_dir = tools_dir / "sdd-compile"
        project_dir.mkdir()
        for filename in ("public.py", "internal.py", "deprecated.py"):
            (tools_dir / filename).write_text("", encoding="utf-8")
        _write_registry(
            tools_dir,
            """
schema_version: "1"
tools:
  - id: public/check
    path: tools/public.py
    visibility: public
    status: active
    runner: uv-python
    description: Public check
  - id: internal/check
    path: tools/internal.py
    visibility: internal
    status: active
    runner: uv-python
    description: Internal check
  - id: old/check
    path: tools/deprecated.py
    visibility: deprecated
    status: deprecated
    runner: uv-python
    description: Old check
    replacement: public/check
  - id: compiler/project
    path: tools/sdd-compile
    visibility: project
    status: active
    runner: go-project
    description: Compiler project
""",
        )
        with patch(
            "providence_cli.commands.tools._find_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["tools", "list", "--all"])
        assert result.exit_code == 0
        assert "public/check" in result.output
        assert "internal/check" in result.output
        assert "old/check" in result.output
        assert "replacement: public/check" in result.output
        assert "compiler/project" in result.output

    def test_manifest_list_json_outputs_machine_readable_entries(
        self, tmp_path: Path
    ) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "public.py").write_text("", encoding="utf-8")
        _write_registry(
            tools_dir,
            """
schema_version: "1"
tools:
  - id: public/check
    path: tools/public.py
    visibility: public
    status: active
    runner: uv-python
    description: Public check
""",
        )
        with patch(
            "providence_cli.commands.tools._find_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["tools", "list", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["source"] == "manifest"
        assert payload["tools"][0]["id"] == "public/check"

    def test_invalid_manifest_reports_schema_error(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        _write_registry(
            tools_dir,
            """
schema_version: "1"
tools:
  - id: bad/path
    path: ../outside.py
    visibility: public
    status: active
    runner: uv-python
    description: Bad path
""",
        )
        with patch(
            "providence_cli.commands.tools._find_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 1
        assert "invalid tools registry" in result.output
        assert "path must stay under tools/" in result.output


class TestToolsRun:
    def test_script_not_found_without_extension_exits_1(self, tmp_path: Path) -> None:
        _make_tools_dir(tmp_path)
        with patch(
            "providence_cli.commands.tools_run._find_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["tools", "run", "missing"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_script_found_with_py_extension_appended(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        script = tools_dir / "check.py"
        script.write_text("", encoding="utf-8")
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(returncode=0)
        with (
            patch(
                "providence_cli.commands.tools_run._find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["tools", "run", "check"])
        assert result.exit_code == 0

    def test_run_success_with_explicit_py_extension(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        script = tools_dir / "tool.py"
        script.write_text("", encoding="utf-8")
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(returncode=0)
        with (
            patch(
                "providence_cli.commands.tools_run._find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["tools", "run", "tool.py"])
        assert result.exit_code == 0
        called_cmd = mock_runner.run.call_args[0][0]
        assert "uv" in called_cmd

    def test_run_passes_extra_args(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "tool.py").write_text("", encoding="utf-8")
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(returncode=0)
        with (
            patch(
                "providence_cli.commands.tools_run._find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["tools", "run", "tool.py", "extra_arg"])
        assert result.exit_code == 0
        called_cmd = mock_runner.run.call_args[0][0]
        assert "extra_arg" in called_cmd

    def test_run_resolves_manifest_id_before_legacy_path(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        manifest_script = tools_dir / "manifest_tool.py"
        manifest_script.write_text("", encoding="utf-8")
        _write_registry(
            tools_dir,
            """
schema_version: "1"
tools:
  - id: maintenance/lint_all
    path: tools/manifest_tool.py
    visibility: public
    status: active
    runner: uv-python
    description: Lint all
""",
        )
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(returncode=0)
        with (
            patch(
                "providence_cli.commands.tools_run._find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["tools", "run", "maintenance/lint_all"])
        assert result.exit_code == 0
        called_cmd = mock_runner.run.call_args[0][0]
        assert str(manifest_script) in called_cmd

    def test_run_resolves_manifest_path_without_tools_prefix(
        self, tmp_path: Path
    ) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        subdir = tools_dir / "maintenance"
        subdir.mkdir()
        script = subdir / "lint_all.py"
        script.write_text("", encoding="utf-8")
        _write_registry(
            tools_dir,
            """
schema_version: "1"
tools:
  - id: maintenance/lint_all
    path: tools/maintenance/lint_all.py
    visibility: public
    status: active
    runner: uv-python
    description: Lint all
""",
        )
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(returncode=0)
        with (
            patch(
                "providence_cli.commands.tools_run._find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["tools", "run", "maintenance/lint_all.py"])
        assert result.exit_code == 0
        called_cmd = mock_runner.run.call_args[0][0]
        assert str(script) in called_cmd

    def test_run_blocks_deprecated_manifest_entry_without_direct_run(
        self, tmp_path: Path
    ) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "old.py").write_text("", encoding="utf-8")
        _write_registry(
            tools_dir,
            """
schema_version: "1"
tools:
  - id: old/check
    path: tools/old.py
    visibility: deprecated
    status: deprecated
    runner: uv-python
    description: Old check
    replacement: new/check
""",
        )
        with patch(
            "providence_cli.commands.tools_run._find_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["tools", "run", "old/check"])
        assert result.exit_code == 1
        assert "not runnable from manifest" in result.output
        assert "replacement: new/check" in result.output

    def test_run_allows_deprecated_manifest_entry_with_direct_run(
        self, tmp_path: Path
    ) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        script = tools_dir / "old.py"
        script.write_text("", encoding="utf-8")
        _write_registry(
            tools_dir,
            """
schema_version: "1"
tools:
  - id: old/check
    path: tools/old.py
    visibility: deprecated
    status: deprecated
    runner: uv-python
    description: Old check
    allow_direct_run: true
""",
        )
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(returncode=0)
        with (
            patch(
                "providence_cli.commands.tools_run._find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["tools", "run", "old/check"])
        assert result.exit_code == 0
        called_cmd = mock_runner.run.call_args[0][0]
        assert str(script) in called_cmd

    def test_run_rejects_go_project_without_command(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        project_dir = tools_dir / "sdd-compile"
        project_dir.mkdir()
        _write_registry(
            tools_dir,
            """
schema_version: "1"
tools:
  - id: compiler/project
    path: tools/sdd-compile
    visibility: project
    status: active
    runner: go-project
    description: Compiler project
    allow_direct_run: true
""",
        )
        with patch(
            "providence_cli.commands.tools_run._find_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["tools", "run", "compiler/project"])
        assert result.exit_code == 1
        assert "runner 'go-project' is not directly executable" in result.output

    def test_authorization_error_exits_2(self, tmp_path: Path) -> None:
        from providence_core.utils.process import ProcessAuthorizationError

        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "tool.py").write_text("", encoding="utf-8")
        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessAuthorizationError("blocked")
        with (
            patch(
                "providence_cli.commands.tools_run._find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["tools", "run", "tool.py"])
        assert result.exit_code == 2
        assert "blocked by policy" in result.output

    def test_spawn_error_exits_127(self, tmp_path: Path) -> None:
        from providence_core.utils.process import ProcessSpawnError

        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "tool.py").write_text("", encoding="utf-8")
        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessSpawnError("uv not found")
        with (
            patch(
                "providence_cli.commands.tools_run._find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["tools", "run", "tool.py"])
        assert result.exit_code == 127
        assert "uv" in result.output

    def test_non_zero_returncode_propagates(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "tool.py").write_text("", encoding="utf-8")
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(returncode=42)
        with (
            patch(
                "providence_cli.commands.tools_run._find_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
        ):
            result = runner.invoke(app, ["tools", "run", "tool.py"])
        assert result.exit_code == 42
