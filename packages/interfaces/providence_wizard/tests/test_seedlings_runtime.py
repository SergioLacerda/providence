"""Tests for seedlings_runtime.run_phase6_seedlings_generation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from providence_wizard.orchestration.wizard.seedlings_runtime import (
    run_phase6_seedlings_generation,
)

_FAKE_PATHS: dict = {
    "client_compiled": Path("/fake/client_compiled"),
}

_PATCHES = (
    "providence_core.utils.environment.get_sdd_paths",
    "providence_wizard.orchestration.wizard.seedlings_runtime.GovernanceLoader",
    "providence_wizard.orchestration.wizard.seedlings_runtime.SeedlingsOrchestrator",
)


def _mock_loader(load_result: bool) -> MagicMock:
    loader = MagicMock()
    loader.load.return_value = load_result
    loader.mandates = []
    loader.guidelines_by_category = {}
    return loader


def _mock_orchestrator(generate_result: bool) -> MagicMock:
    orch = MagicMock()
    orch.generate.return_value = generate_result
    return orch


def _run(
    tmp_path: Path,
    loader: MagicMock,
    orchestrator: MagicMock,
    config_path: Path | None = None,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    with (
        patch(_PATCHES[0], return_value=_FAKE_PATHS),
        patch(_PATCHES[1], return_value=loader),
        patch(_PATCHES[2], return_value=orchestrator),
    ):
        result = run_phase6_seedlings_generation(
            wizard_config_path=config_path or (tmp_path / "cfg.json"),
            output_base=tmp_path,
            emitter=messages.append,
        )
    return result, messages


class TestRunPhase6SeedlingsGeneration:
    def test_loads_config_from_file_when_present(self, tmp_path: Path) -> None:
        config_path = tmp_path / "wizard-config.json"
        config_path.write_text(json.dumps({"language": "TypeScript"}), encoding="utf-8")
        result, _ = _run(
            tmp_path, _mock_loader(True), _mock_orchestrator(True), config_path
        )
        assert result is True

    def test_uses_default_config_when_file_missing(self, tmp_path: Path) -> None:
        result, _ = _run(tmp_path, _mock_loader(True), _mock_orchestrator(True))
        assert result is True

    def test_default_config_includes_language_context(self, tmp_path: Path) -> None:
        loader = _mock_loader(True)
        orchestrator = _mock_orchestrator(True)
        with (
            patch(_PATCHES[0], return_value=_FAKE_PATHS),
            patch(_PATCHES[1], return_value=loader),
            patch(_PATCHES[2], return_value=orchestrator) as orchestrator_cls,
        ):
            result = run_phase6_seedlings_generation(
                wizard_config_path=tmp_path / "missing.json",
                output_base=tmp_path,
                emitter=lambda _msg: None,
            )
        assert result is True
        assert loader.load.called
        assert "language_context" in orchestrator_cls.call_args.kwargs["config"]

    def test_returns_false_when_loader_fails(self, tmp_path: Path) -> None:
        result, messages = _run(tmp_path, _mock_loader(False), _mock_orchestrator(True))
        assert result is False
        assert any("Failed to load governance" in m for m in messages)

    def test_returns_false_when_orchestrator_fails(self, tmp_path: Path) -> None:
        result, messages = _run(tmp_path, _mock_loader(True), _mock_orchestrator(False))
        assert result is False
        assert any("Failed to generate" in m for m in messages)

    def test_emits_success_message_on_completion(self, tmp_path: Path) -> None:
        result, messages = _run(tmp_path, _mock_loader(True), _mock_orchestrator(True))
        assert result is True
        assert any("seedlings" in m.lower() for m in messages)
