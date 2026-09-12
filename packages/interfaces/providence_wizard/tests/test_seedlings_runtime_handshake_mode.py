"""Tests for handshake_mode-driven seedling selection in Phase 6."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from providence_wizard.orchestration.wizard.seedlings_runtime import (
    run_phase6_seedlings_generation,
)

pytestmark = pytest.mark.unit


def _write_config(path: Path, handshake_mode: str | None) -> None:
    config = {"language": "Python", "enforcement_mode": "warn_mode"}
    if handshake_mode is not None:
        config["handshake_mode"] = handshake_mode
    path.write_text(json.dumps(config), encoding="utf-8")


class TestHandshakeModeSeedlingSelection:
    @patch(
        "providence_wizard.orchestration.wizard.seedlings_runtime.SeedlingsOrchestrator"
    )
    @patch("providence_wizard.orchestration.wizard.seedlings_runtime.GovernanceLoader")
    def test_hook_mode_restricts_selection_to_hook_capable_platforms(
        self, mock_loader_cls, mock_orchestrator_cls, tmp_path: Path
    ) -> None:
        config_path = tmp_path / "wizard-config.json"
        _write_config(config_path, "hook")
        mock_loader_cls.return_value.load.return_value = True
        mock_orchestrator = mock_orchestrator_cls.return_value
        mock_orchestrator.generate.return_value = True

        run_phase6_seedlings_generation(
            wizard_config_path=config_path, output_base=tmp_path, emitter=lambda _: None
        )

        _, kwargs = mock_orchestrator.generate.call_args
        selected = kwargs["selected"]
        assert selected is not None
        for excluded in ("copilot", "cursor", "vscode"):
            assert excluded not in selected
        for included in ("claude", "codex", "gemini"):
            assert included in selected
        assert (
            tmp_path / ".providence" / "runtime" / "hooks" / "prompt-submit.py"
        ).exists()
        assert (tmp_path / ".codex" / "config.toml").exists()

    @patch(
        "providence_wizard.orchestration.wizard.seedlings_runtime.SeedlingsOrchestrator"
    )
    @patch("providence_wizard.orchestration.wizard.seedlings_runtime.GovernanceLoader")
    def test_standard_mode_generates_all_seedlings(
        self, mock_loader_cls, mock_orchestrator_cls, tmp_path: Path
    ) -> None:
        config_path = tmp_path / "wizard-config.json"
        _write_config(config_path, "standard")
        mock_loader_cls.return_value.load.return_value = True
        mock_orchestrator = mock_orchestrator_cls.return_value
        mock_orchestrator.generate.return_value = True

        run_phase6_seedlings_generation(
            wizard_config_path=config_path, output_base=tmp_path, emitter=lambda _: None
        )

        mock_orchestrator.generate.assert_called_once_with(selected=None)
