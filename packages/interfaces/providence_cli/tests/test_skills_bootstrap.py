"""Unit tests for providence_cli.services.skills_bootstrap  governance validation and full bootstrap."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from providence_cli.services.skills_bootstrap import (
    handle_adapter_error,
    run_full_bootstrap,
    run_reconcile,
    validate_and_load_governance,
)


class TestValidateAndLoadGovernance:
    def test_text_mode_exits_on_invalid_path(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        with (
            patch(
                "providence_cli.services.skills_bootstrap_validation.validate_governance_path",
                return_value=False,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            validate_and_load_governance(
                tmp_path / ".providence" / "compiled",
                output_json=False,
                emit_fn=mock_emit,
            )
        assert exc_info.value.exit_code == 1
        mock_emit.assert_not_called()

    def test_json_mode_exits_on_invalid_path(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        with (
            patch(
                "providence_cli.services.skills_bootstrap_validation.validate_governance_path",
                return_value=False,
            ),
            pytest.raises(typer.Exit),
        ):
            validate_and_load_governance(
                tmp_path / ".providence" / "compiled",
                output_json=True,
                emit_fn=mock_emit,
            )
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["error_code"] == "missing_governance_artifacts"

    def test_text_mode_exits_on_empty_items(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        with (
            patch(
                "providence_cli.services.skills_bootstrap_validation.validate_governance_path",
                return_value=True,
            ),
            patch(
                "providence_cli.services.skills_bootstrap_validation.load_governance_config",
                return_value={"items": []},
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            validate_and_load_governance(
                tmp_path / ".providence" / "compiled",
                output_json=False,
                emit_fn=mock_emit,
            )
        assert exc_info.value.exit_code == 1

    def test_json_mode_exits_on_empty_items(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        with (
            patch(
                "providence_cli.services.skills_bootstrap_validation.validate_governance_path",
                return_value=True,
            ),
            patch(
                "providence_cli.services.skills_bootstrap_validation.load_governance_config",
                return_value={"items": []},
            ),
            pytest.raises(typer.Exit),
        ):
            validate_and_load_governance(
                tmp_path / ".providence" / "compiled",
                output_json=True,
                emit_fn=mock_emit,
            )
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["error_code"] == "missing_governance_items"


class TestRunReconcile:
    def test_text_mode_exits_on_exception(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        with (
            patch(
                "providence_cli.services.skills_bootstrap._reconcile_root_seed_artifacts",
                side_effect=FileNotFoundError("no registry"),
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_reconcile(tmp_path, dry_run=False, output_json=False, emit_fn=mock_emit)
        assert exc_info.value.exit_code == 1
        mock_emit.assert_not_called()

    def test_json_mode_exits_on_exception(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        with (
            patch(
                "providence_cli.services.skills_bootstrap._reconcile_root_seed_artifacts",
                side_effect=FileNotFoundError("no registry"),
            ),
            pytest.raises(typer.Exit),
        ):
            run_reconcile(tmp_path, dry_run=False, output_json=True, emit_fn=mock_emit)
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["error_code"] == "seed_reconciliation_failed"


class TestRunFullBootstrap:
    def _make_reconcile_summary(self) -> MagicMock:
        summary = MagicMock()
        summary.as_json.return_value = {}
        summary.commands = {"added": 2, "removed": 0}
        summary.skills = {"added": 3, "removed": 0}
        return summary

    def test_text_mode_prints_completion_summary(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        reconcile_summary = self._make_reconcile_summary()

        with (
            patch(
                "providence_cli.services.skills_bootstrap.validate_and_load_governance",
                return_value={"items": [{}]},
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_agent_seeds",
                return_value=[1, 2],
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_agent_instruction_files"
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_agent_prompt_commands"
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_skills_registry",
                return_value={"skill_count": 5},
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_commands_registry",
                return_value={"command_count": 3},
            ),
            patch(
                "providence_cli.services.skills_bootstrap.reconcile_registries",
                return_value=reconcile_summary,
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_skill_index",
                return_value={"skill_count": 5},
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_cli_commands_index",
                return_value={"command_count": 3},
            ),
            patch(
                "providence_cli.services.skills_bootstrap._generate_adapters",
                return_value=(2, None),
            ),
        ):
            run_full_bootstrap(
                tmp_path,
                regenerate_seeds=False,
                dry_run=False,
                output_json=False,
                emit_fn=mock_emit,
            )
        mock_emit.assert_not_called()

    def test_text_mode_prints_deleted_seeds_on_regenerate(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        reconcile_summary = self._make_reconcile_summary()

        with (
            patch(
                "providence_cli.services.skills_bootstrap.validate_and_load_governance",
                return_value={"items": [{}]},
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_agent_seeds",
                return_value=[],
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_agent_instruction_files"
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_agent_prompt_commands"
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_skills_registry",
                return_value={"skill_count": 0},
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_commands_registry",
                return_value={"command_count": 0},
            ),
            patch(
                "providence_cli.services.skills_bootstrap.reconcile_registries",
                return_value=reconcile_summary,
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_skill_index",
                return_value={"skill_count": 0},
            ),
            patch(
                "providence_cli.services.skills_bootstrap.generate_cli_commands_index",
                return_value={"command_count": 0},
            ),
            patch(
                "providence_cli.services.skills_bootstrap._generate_adapters",
                return_value=(0, None),
            ),
            patch(
                "providence_cli.services.skills_bootstrap.run_reconcile",
                return_value=(3, 3),
            ),
        ):
            run_full_bootstrap(
                tmp_path,
                regenerate_seeds=True,
                dry_run=False,
                output_json=False,
                emit_fn=mock_emit,
            )
        mock_emit.assert_not_called()


class TestHandleAdapterError:
    def test_text_mode_prints_error_and_exits(self) -> None:
        mock_emit = MagicMock()
        with pytest.raises(typer.Exit) as exc_info:
            handle_adapter_error("template error", output_json=False, emit_fn=mock_emit)
        assert exc_info.value.exit_code == 1
        mock_emit.assert_not_called()

    def test_json_mode_emits_error_and_exits(self) -> None:
        mock_emit = MagicMock()
        with pytest.raises(typer.Exit) as exc_info:
            handle_adapter_error("template error", output_json=True, emit_fn=mock_emit)
        assert exc_info.value.exit_code == 1
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["error_code"] == "adapter_generation_failed"
