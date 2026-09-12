"""Tests for sdd claude commands (Soft/Standalone governance projection build)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import providence_cli.commands.claude as claude_mod

runner = CliRunner()
claude_app = claude_mod.app


def test_claude_build_writes_standalone_surface(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(claude_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(claude_app, ["build"])

    assert result.exit_code == 0, result.output
    bundle = tmp_path / "dist" / "claude-standalone"
    assert (bundle / "CLAUDE.md").exists()
    assert (bundle / ".claude" / "settings.json").exists()
    assert (bundle / ".claude" / "rules" / "go.md").exists()
    # Never written to the project's real root files.
    assert not (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / ".claude").exists()


def test_claude_build_accepts_custom_dest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(claude_mod, "resolve_workspace_root", lambda: tmp_path)
    custom_dest = tmp_path / "custom-out"

    result = runner.invoke(claude_app, ["build", "--dest", str(custom_dest)])

    assert result.exit_code == 0, result.output
    assert (custom_dest / "CLAUDE.md").exists()
