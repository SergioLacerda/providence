"""Tests for the seedling application bridge."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from providence_wizard.application.seedling_bridge import SeedlingBridge


def test_seedling_bridge_returns_true_on_success(tmp_path: Path) -> None:
    with patch(
        "providence_wizard.orchestration.wizard.seedlings_runtime.run_phase6_seedlings_generation",
        return_value=True,
    ):
        result = SeedlingBridge().generate(
            tmp_path / "wizard-config.json", tmp_path, lambda _: None
        )
    assert result is True


def test_seedling_bridge_returns_false_on_exception(tmp_path: Path) -> None:
    messages: list[str] = []
    with patch(
        "providence_wizard.orchestration.wizard.seedlings_runtime.run_phase6_seedlings_generation",
        side_effect=RuntimeError("boom"),
    ):
        result = SeedlingBridge().generate(
            tmp_path / "wizard-config.json",
            tmp_path,
            messages.append,
        )
    assert result is False
    assert any("boom" in message for message in messages)
