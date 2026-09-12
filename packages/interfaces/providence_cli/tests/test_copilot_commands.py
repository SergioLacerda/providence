"""Tests for sdd copilot commands (Soft/Standalone governance projection build)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import providence_cli.commands.copilot as copilot_mod

runner = CliRunner()
copilot_app = copilot_mod.app


def test_copilot_build_writes_standalone_surface(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(copilot_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(copilot_app, ["build"])

    assert result.exit_code == 0, result.output
    bundle = tmp_path / "dist" / "copilot-standalone"
    assert (bundle / ".github" / "copilot-instructions.md").exists()
    assert (bundle / ".github" / "instructions" / "go.instructions.md").exists()
    # Never written to the project's real .github/ files.
    assert not (tmp_path / ".github").exists()


def test_copilot_build_accepts_custom_dest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(copilot_mod, "resolve_workspace_root", lambda: tmp_path)
    custom_dest = tmp_path / "custom-out"

    result = runner.invoke(copilot_app, ["build", "--dest", str(custom_dest)])

    assert result.exit_code == 0, result.output
    assert (custom_dest / ".github" / "copilot-instructions.md").exists()
