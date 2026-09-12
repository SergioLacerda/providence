"""Tests for providence_cli.services.governance_generate_handlers  bootstrap and artifact generation."""

from __future__ import annotations

import io
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from rich.console import Console

from providence_cli.services.governance_bootstrap_handlers import (
    complete_bootstrap_handshake,
    run_bootstrap_signing,
)
from providence_cli.services.governance_generate_handlers import generate_artifacts


def _console() -> Console:
    return Console(file=io.StringIO(), width=120)


class _FakeChallenge:
    def __init__(self) -> None:
        self.active_mandates = ["M001", "M002"]
        self.available_skills = [
            {"name": "sdd-ask"},
            {"name": "sdd-organize"},
            "not-a-dict",
            {"no_name": "x"},
            {"name": 123},
        ]


class _FakeAHP:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def generate_challenge(
        self, task_description: str = "General Task"
    ) -> _FakeChallenge:
        assert task_description == "Bootstrap Session"
        return _FakeChallenge()

    def complete_handshake(self, response: dict) -> None:
        self.response = response


class TestCompleteBootstrapHandshake:
    def test_filters_invalid_skill_entries(self) -> None:
        captured: dict = {}

        class _CapturingAHP(_FakeAHP):
            def complete_handshake(self, response: dict) -> None:
                captured.update(response)

        with patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol", _CapturingAHP
        ):
            complete_bootstrap_handshake()

        assert captured["skills_to_use"] == ["sdd-ask", "sdd-organize"]
        assert captured["understood_mandates"] == ["M001", "M002"]
        assert captured["acknowledged_signature"] is True
        assert captured["compliance_declaration"] is True

    def test_uses_resolved_workspace_root_not_cwd_default(self, tmp_path: Path) -> None:
        """Bootstrap must target the resolved workspace root explicitly, not
        AgentHandshakeProtocol()'s cwd-based default, so full-bootstrap in an
        isolated test/CI workspace never touches the real repository root."""
        captured_kwargs: dict = {}

        class _CapturingRootAHP(_FakeAHP):
            def __init__(self, *args, **kwargs) -> None:
                captured_kwargs.update(kwargs)
                super().__init__(*args, **kwargs)

        with (
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                _CapturingRootAHP,
            ),
            patch(
                "providence_cli.services.governance_bootstrap_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
        ):
            complete_bootstrap_handshake()

        assert captured_kwargs.get("project_root") == tmp_path


class TestRunBootstrapSigning:
    def test_normal_flow_signs_once(self, tmp_path: Path) -> None:
        keygen_fn = MagicMock()
        sign_fn = MagicMock()
        with patch(
            "providence_cli.services.governance_bootstrap_handlers.resolve_workspace_root",
            return_value=tmp_path,
        ):
            run_bootstrap_signing("dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn)

        keygen_fn.assert_called_once_with(
            key_id="dev-01", output_dir=".providence/trust"
        )
        sign_fn.assert_called_once_with(
            key_id="dev-01", key_path=None, compiled_dir=None, source=False
        )

    def test_keygen_exit_zero_is_tolerated(self, tmp_path: Path) -> None:
        keygen_fn = MagicMock(side_effect=typer.Exit(0))
        sign_fn = MagicMock()
        with patch(
            "providence_cli.services.governance_bootstrap_handlers.resolve_workspace_root",
            return_value=tmp_path,
        ):
            run_bootstrap_signing("dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn)
        sign_fn.assert_called_once()

    def test_existing_key_then_signing_failure_is_reraised(
        self, tmp_path: Path
    ) -> None:
        keygen_fn = MagicMock(side_effect=typer.Exit(0))
        sign_fn = MagicMock(side_effect=typer.Exit(1))
        with (
            patch(
                "providence_cli.services.governance_bootstrap_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_bootstrap_signing("dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn)

        assert exc_info.value.exit_code == 1
        keygen_fn.assert_called_once_with(
            key_id="dev-01", output_dir=".providence/trust"
        )
        sign_fn.assert_called_once_with(
            key_id="dev-01", key_path=None, compiled_dir=None, source=False
        )

    def test_keygen_exit_nonzero_is_reraised(self, tmp_path: Path) -> None:
        keygen_fn = MagicMock(side_effect=typer.Exit(1))
        sign_fn = MagicMock()
        with (
            patch(
                "providence_cli.services.governance_bootstrap_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_bootstrap_signing("dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn)
        assert exc_info.value.exit_code == 1
        sign_fn.assert_not_called()

    def test_source_artifact_present_signs_twice(self, tmp_path: Path) -> None:
        source_dir = tmp_path / ".providence" / "source"
        source_dir.mkdir(parents=True)
        (source_dir / "governance-core.json").write_text("{}", encoding="utf-8")

        keygen_fn = MagicMock()
        sign_fn = MagicMock()
        with patch(
            "providence_cli.services.governance_bootstrap_handlers.resolve_workspace_root",
            return_value=tmp_path,
        ):
            run_bootstrap_signing("dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn)

        assert sign_fn.call_count == 2
        sign_fn.assert_any_call(
            key_id="dev-01", key_path=None, compiled_dir=None, source=True
        )

    def test_no_workspace_skips_source_sign(self) -> None:
        keygen_fn = MagicMock()
        sign_fn = MagicMock()
        with patch(
            "providence_cli.services.governance_bootstrap_handlers.resolve_workspace_root",
            return_value=None,
        ):
            run_bootstrap_signing("dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn)
        sign_fn.assert_called_once()


class TestGenerateArtifacts:
    def _common_patches(self, tmp_path: Path, *, items: list | None = None):
        items = items if items is not None else [{"id": "M001"}]
        return (
            patch(
                "providence_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.resolve_generate_path",
                return_value=str(tmp_path / "compiled"),
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.validate_governance_path",
                return_value=True,
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.load_governance_config",
                return_value={"items": items},
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.resolve_output_base",
                side_effect=lambda p: p,
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.generate_seeds",
                return_value=(
                    [("copilot", tmp_path / "a.md", "ok")],
                    tmp_path / "seeds",
                ),
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.run_generate_phases",
                return_value=(True, True, True),
            ),
        )

    def test_invalid_governance_path_exits(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.resolve_generate_path",
                return_value=str(tmp_path / "compiled"),
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.validate_governance_path",
                return_value=False,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            generate_artifacts(
                output_dir=str(tmp_path), path="", output_json=False, console=_console()
            )
        assert exc_info.value.exit_code == 1

    def test_missing_items_exits(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.resolve_generate_path",
                return_value=str(tmp_path / "compiled"),
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.validate_governance_path",
                return_value=True,
            ),
            patch(
                "providence_cli.services.governance_generate_handlers.load_governance_config",
                return_value={"items": []},
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            generate_artifacts(
                output_dir=str(tmp_path), path="", output_json=False, console=_console()
            )
        assert exc_info.value.exit_code == 1

    def test_output_dir_none_resolves_workspace_root(self, tmp_path: Path) -> None:
        with ExitStack() as stack:
            for p in self._common_patches(tmp_path):
                stack.enter_context(p)
            stack.enter_context(
                patch(
                    "providence_cli.services.governance_generate_handlers.render_generate_table"
                )
            )
            stack.enter_context(
                patch(
                    "providence_cli.services.governance_generate_handlers.write_instruction_files_safe"
                )
            )
            stack.enter_context(
                patch(
                    "providence_cli.services.governance_generate_handlers.write_prompt_commands_safe"
                )
            )
            stack.enter_context(
                patch(
                    "providence_cli.services.governance_generate_handlers.generate_adapters_safe"
                )
            )
            stack.enter_context(
                patch(
                    "providence_cli.services.governance_generate_handlers.generate_runtime_handbook_required"
                )
            )
            generate_artifacts(
                output_dir=None, path="", output_json=False, console=_console()
            )

    def test_output_json_emits_payload(self, tmp_path: Path) -> None:
        with ExitStack() as stack:
            for p in self._common_patches(tmp_path):
                stack.enter_context(p)
            mock_json = stack.enter_context(
                patch(
                    "providence_cli.services.governance_generate_handlers.run_governance_generate_json",
                    return_value={"status": "ok"},
                )
            )
            mock_emit = stack.enter_context(
                patch("providence_cli.services.governance_generate_handlers.emit_json")
            )
            mock_handbook = stack.enter_context(
                patch(
                    "providence_cli.services.governance_generate_handlers.generate_runtime_handbook_required"
                )
            )
            generate_artifacts(
                output_dir=str(tmp_path), path="", output_json=True, console=_console()
            )
        mock_json.assert_called_once()
        mock_emit.assert_called_once_with({"status": "ok"})
        mock_handbook.assert_called_once()
        assert mock_handbook.call_args.kwargs["quiet"] is True

    def test_non_json_renders_table_and_writes_files(self, tmp_path: Path) -> None:
        with ExitStack() as stack:
            for p in self._common_patches(tmp_path):
                stack.enter_context(p)
            mock_table = stack.enter_context(
                patch(
                    "providence_cli.services.governance_generate_handlers.render_generate_table"
                )
            )
            mock_instr = stack.enter_context(
                patch(
                    "providence_cli.services.governance_generate_handlers.write_instruction_files_safe"
                )
            )
            mock_prompt = stack.enter_context(
                patch(
                    "providence_cli.services.governance_generate_handlers.write_prompt_commands_safe"
                )
            )
            mock_adapters = stack.enter_context(
                patch(
                    "providence_cli.services.governance_generate_handlers.generate_adapters_safe"
                )
            )
            mock_handbook = stack.enter_context(
                patch(
                    "providence_cli.services.governance_generate_handlers.generate_runtime_handbook_required"
                )
            )
            generate_artifacts(
                output_dir=str(tmp_path), path="", output_json=False, console=_console()
            )
        mock_table.assert_called_once()
        mock_instr.assert_called_once()
        mock_prompt.assert_called_once()
        mock_adapters.assert_called_once()
        mock_handbook.assert_called_once()
        assert mock_handbook.call_args.kwargs["quiet"] is False
