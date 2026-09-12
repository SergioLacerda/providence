"""Tests for sdd devin commands (Soft/Standalone governance plugin build)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import providence_cli.commands.devin as devin_mod

runner = CliRunner()
devin_app = devin_mod.app


def _write_minimal_registry(ws_root: Path) -> None:
    skills_dir = ws_root / ".providence" / "skills" / "alpha"
    skills_dir.mkdir(parents=True)
    (ws_root / ".providence" / "skills" / "registry.json").write_text(
        json.dumps({"skills": [{"name": "alpha"}]}), encoding="utf-8"
    )
    (skills_dir / "skill.yaml").write_text(
        "name: alpha\ndescription: test skill\n", encoding="utf-8"
    )


def test_devin_build_writes_plugin_bundle(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_registry(tmp_path)
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(devin_app, ["build"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "dist" / "devin-plugin" / "AGENTS.md").exists()


def test_devin_build_reports_failure_when_no_skills(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(devin_app, ["build"])

    assert result.exit_code == 1
    assert "failed" in result.output.lower()


def test_devin_build_accepts_custom_dest(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_registry(tmp_path)
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)
    custom_dest = tmp_path / "custom-out"

    result = runner.invoke(devin_app, ["build", "--dest", str(custom_dest)])

    assert result.exit_code == 0, result.output
    assert (custom_dest / "AGENTS.md").exists()


def test_devin_build_standalone_writes_zero_sdd_config(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(devin_app, ["build", "--standalone"])

    assert result.exit_code == 0, result.output
    bundle = tmp_path / "dist" / "devin-standalone"
    assert (bundle / "AGENTS.md").exists()
    assert (bundle / ".devin" / "config.json").exists()
    # Never written to the project's real root files.
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / ".devin").exists()


def test_devin_build_standalone_accepts_custom_dest(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)
    custom_dest = tmp_path / "custom-out"

    result = runner.invoke(
        devin_app, ["build", "--standalone", "--dest", str(custom_dest)]
    )

    assert result.exit_code == 0, result.output
    assert (custom_dest / "AGENTS.md").exists()


def test_devin_build_standalone_and_skills_are_mutually_exclusive(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(devin_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(devin_app, ["build", "--standalone", "--skills"])

    assert result.exit_code == 1
    assert not (tmp_path / "dist").exists()
