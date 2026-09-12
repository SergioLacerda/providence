"""Tests for providence_cli.services.governance_generate_handlers."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from rich.console import Console

from providence_cli.services.governance_generate_handlers import (
    generate_seeds,
    resolve_generate_path,
    run_generate_phases,
)
from providence_cli.services.governance_generate_prereqs import (
    generate_adapters_safe,
    generate_runtime_handbook_required,
    write_instruction_files_safe,
    write_prompt_commands_safe,
)


def _console() -> Console:
    return Console(file=io.StringIO(), width=120)


class TestResolveGeneratePath:
    def test_returns_path_when_given(self) -> None:
        assert resolve_generate_path("/some/path") == "/some/path"

    def test_no_workspace_raises_exit(self) -> None:
        with (
            patch(
                "providence_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=None,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            resolve_generate_path("")
        assert exc_info.value.exit_code == 1

    def test_empty_path_resolves_to_compiled_dir(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.enforce_path_policy",
                side_effect=lambda root, **_: root,
            ),
        ):
            result = resolve_generate_path("")
        assert result == str(tmp_path / ".providence" / "compiled")


class TestGenerateSeeds:
    def test_returns_seeds_info_and_dir(self, tmp_path: Path) -> None:
        fake_seeds_info = [("copilot", tmp_path / "a.md", "ok")]
        with patch(
            "providence_cli.services.governance_generate_handlers.generate_agent_seeds",
            return_value=fake_seeds_info,
        ) as mock_gen:
            seeds_info, seeds_dir = generate_seeds(str(tmp_path), {"items": []})
        assert seeds_info == fake_seeds_info
        assert seeds_dir == tmp_path / ".vscode" / "agents"
        mock_gen.assert_called_once_with(seeds_dir, {"items": []})


class TestWriteInstructionFilesSafe:
    def test_success_prints_written_message(self, tmp_path: Path) -> None:
        console = _console()
        with patch(
            "providence_cli.services.governance_generate_prereqs.generate_agent_instruction_files",
            return_value=[("copilot", tmp_path / "a.md")],
        ):
            write_instruction_files_safe(tmp_path, {}, console=console)
        output = console.file.getvalue()
        assert "copilot instructions written to" in output

    def test_exception_prints_warning(self, tmp_path: Path) -> None:
        console = _console()
        with patch(
            "providence_cli.services.governance_generate_prereqs.generate_agent_instruction_files",
            side_effect=RuntimeError("boom"),
        ):
            write_instruction_files_safe(tmp_path, {}, console=console)
        output = console.file.getvalue()
        assert "could not write instruction files" in output


class TestWritePromptCommandsSafe:
    def test_success_prints_written_message(self, tmp_path: Path) -> None:
        console = _console()
        with patch(
            "providence_cli.services.governance_generate_prereqs.generate_agent_prompt_commands",
            return_value=[("codex", tmp_path / "commands.md")],
        ):
            write_prompt_commands_safe(tmp_path, {}, console=console)
        output = console.file.getvalue()
        assert "codex prompt commands written to" in output

    def test_exception_prints_warning(self, tmp_path: Path) -> None:
        console = _console()
        with patch(
            "providence_cli.services.governance_generate_prereqs.generate_agent_prompt_commands",
            side_effect=RuntimeError("boom"),
        ):
            write_prompt_commands_safe(tmp_path, {}, console=console)
        output = console.file.getvalue()
        assert "could not write prompt command files" in output


class TestGenerateAdaptersSafe:
    def test_success_with_files_written(self, tmp_path: Path) -> None:
        console = _console()
        result = MagicMock(success=True, files_written=["a", "b"], errors=[])
        fake_gen = MagicMock()
        fake_gen.generate.return_value = {"claude": result}
        with patch(
            "providence_adapters.adapter_generator.AdapterGenerator",
            return_value=fake_gen,
        ):
            generate_adapters_safe(tmp_path, console=console)
        output = console.file.getvalue()
        assert "Adapters (claude): 2 files written" in output

    def test_errors_print_warnings(self, tmp_path: Path) -> None:
        console = _console()
        result = MagicMock(success=False, files_written=[], errors=["bad thing"])
        fake_gen = MagicMock()
        fake_gen.generate.return_value = {"claude": result}
        with patch(
            "providence_adapters.adapter_generator.AdapterGenerator",
            return_value=fake_gen,
        ):
            generate_adapters_safe(tmp_path, console=console)
        output = console.file.getvalue()
        assert "WARN: adapter claude: bad thing" in output

    def test_exception_prints_warning(self, tmp_path: Path) -> None:
        console = _console()
        with patch(
            "providence_adapters.adapter_generator.AdapterGenerator",
            side_effect=RuntimeError("boom"),
        ):
            generate_adapters_safe(tmp_path, console=console)
        output = console.file.getvalue()
        assert "could not generate adapter files" in output


class TestGenerateRuntimeHandbookRequired:
    def test_success_prints_written_count(self, tmp_path: Path) -> None:
        console = _console()
        workspace = tmp_path / "workspace"
        registry = workspace / "docs/spec/canonical/governance-sources.yaml"
        registry.parent.mkdir(parents=True)
        registry.write_text("schema_version: '1'\nsources: []\n", encoding="utf-8")
        with (
            patch(
                "providence_cli.utils.providence_authority.resolve_workspace_root",
                return_value=workspace,
            ),
            patch(
                "providence_cli.services.governance_docs_handbook_gen.generate_runtime_handbook",
                return_value=[tmp_path / ".providence/source/handbook/index.yaml"],
            ) as mock_generate,
        ):
            generate_runtime_handbook_required(tmp_path / "out", console=console)

        mock_generate.assert_called_once_with(workspace, runtime_root=tmp_path / "out")
        assert "Runtime handbook: 1 files written" in console.file.getvalue()

    def test_missing_workspace_registry_uses_repo_sources(self, tmp_path: Path) -> None:
        console = _console()
        with (
            patch(
                "providence_cli.utils.providence_authority.resolve_workspace_root",
                return_value=tmp_path / "workspace",
            ),
            patch(
                "providence_cli.services.governance_docs_handbook_gen.generate_runtime_handbook",
                return_value=[],
            ) as mock_generate,
        ):
            generate_runtime_handbook_required(tmp_path / "out", console=console)

        args, kwargs = mock_generate.call_args
        assert args[0] != tmp_path / "workspace"
        assert (args[0] / "docs/spec/canonical/governance-sources.yaml").exists()
        assert kwargs == {"runtime_root": tmp_path / "out"}

    def test_missing_workspace_registry_without_repo_skips_handbook(
        self, tmp_path: Path
    ) -> None:
        console = _console()
        workspace = tmp_path / "workspace"
        with (
            patch(
                "providence_cli.utils.providence_authority.resolve_workspace_root",
                return_value=workspace,
            ),
            patch(
                "providence_cli.utils.environment.detect_repo_root",
                side_effect=RuntimeError("repo missing"),
            ),
            patch(
                "providence_cli.services.governance_docs_handbook_gen.generate_runtime_handbook",
                return_value=[],
            ) as mock_generate,
        ):
            generate_runtime_handbook_required(tmp_path / "out", console=console)

        mock_generate.assert_called_once_with(workspace, runtime_root=tmp_path / "out")
        assert console.file.getvalue() == ""

    def test_quiet_suppresses_success_output(self, tmp_path: Path) -> None:
        console = _console()
        with patch(
            "providence_cli.services.governance_docs_handbook_gen.generate_runtime_handbook",
            return_value=[tmp_path / ".providence/source/handbook/index.yaml"],
        ):
            generate_runtime_handbook_required(tmp_path, console=console, quiet=True)

        assert console.file.getvalue() == ""

    def test_exception_propagates(self, tmp_path: Path) -> None:
        console = _console()
        with (
            patch(
                "providence_cli.services.governance_docs_handbook_gen.generate_runtime_handbook",
                side_effect=RuntimeError("boom"),
            ),
            pytest.raises(RuntimeError, match="boom"),
        ):
            generate_runtime_handbook_required(tmp_path, console=console)


class TestRunGeneratePhases:
    def test_all_phases_succeed(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_cli.generators._skills.generate_skills_registry",
                return_value={"skill_count": 5},
            ),
            patch(
                "providence_cli.generators._commands.generate_commands_registry",
                return_value={"command_count": 3},
            ),
            patch(
                "providence_cli.generators._indices.generate_skill_index",
                return_value={"skill_count": 5},
            ),
            patch(
                "providence_cli.generators._indices.generate_cli_commands_index",
                return_value={"command_count": 3},
            ),
        ):
            result = run_generate_phases(str(tmp_path), {})
        assert result == (True, True, True)

    def test_zero_counts_yield_false_flags(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_cli.generators._skills.generate_skills_registry",
                return_value={"skill_count": 0},
            ),
            patch(
                "providence_cli.generators._commands.generate_commands_registry",
                return_value={"command_count": 0},
            ),
            patch(
                "providence_cli.generators._indices.generate_skill_index",
                return_value={"skill_count": 0},
            ),
            patch(
                "providence_cli.generators._indices.generate_cli_commands_index",
                return_value={"command_count": 0},
            ),
        ):
            result = run_generate_phases(str(tmp_path), {})
        assert result == (False, False, False)

    def test_all_phases_raise_are_tolerated(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_cli.generators._skills.generate_skills_registry",
                side_effect=RuntimeError("boom"),
            ),
            patch(
                "providence_cli.generators._commands.generate_commands_registry",
                side_effect=RuntimeError("boom"),
            ),
            patch(
                "providence_cli.generators._indices.generate_skill_index",
                side_effect=RuntimeError("boom"),
            ),
            patch(
                "providence_cli.generators._indices.generate_cli_commands_index",
                side_effect=RuntimeError("boom"),
            ),
        ):
            result = run_generate_phases(str(tmp_path), {})
        assert result == (False, False, False)
