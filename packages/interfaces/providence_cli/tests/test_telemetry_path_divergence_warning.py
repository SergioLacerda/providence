"""Tests for the SDD_COMPLIANCE_EVENTS_PATH / SDD_TELEMETRY_PATH divergence warning."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()


def _patch_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: tmp_path,
    )


def test_warns_when_paths_diverge(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv("SDD_COMPLIANCE_EVENTS_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("SDD_TELEMETRY_PATH", str(tmp_path / "b.jsonl"))
    result = runner.invoke(app, ["telemetry", "status"])
    assert "SDD_COMPLIANCE_EVENTS_PATH" in result.output
    assert "SDD_TELEMETRY_PATH" in result.output


def test_no_warning_when_paths_match(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    same_path = str(tmp_path / "same.jsonl")
    monkeypatch.setenv("SDD_COMPLIANCE_EVENTS_PATH", same_path)
    monkeypatch.setenv("SDD_TELEMETRY_PATH", same_path)
    result = runner.invoke(app, ["telemetry", "status"])
    assert "diverge" not in result.output.lower()


def test_no_warning_when_only_compliance_set(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv("SDD_COMPLIANCE_EVENTS_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)
    result = runner.invoke(app, ["telemetry", "status"])
    assert "diverge" not in result.output.lower()


def test_no_warning_when_only_telemetry_set(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.delenv("SDD_COMPLIANCE_EVENTS_PATH", raising=False)
    monkeypatch.setenv("SDD_TELEMETRY_PATH", str(tmp_path / "b.jsonl"))
    result = runner.invoke(app, ["telemetry", "status"])
    assert "diverge" not in result.output.lower()


def test_no_warning_when_neither_set(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.delenv("SDD_COMPLIANCE_EVENTS_PATH", raising=False)
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)
    result = runner.invoke(app, ["telemetry", "status"])
    assert "diverge" not in result.output.lower()


def test_warning_fires_across_subcommands(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv("SDD_COMPLIANCE_EVENTS_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("SDD_TELEMETRY_PATH", str(tmp_path / "b.jsonl"))
    for args in (
        ["telemetry", "dump"],
        ["telemetry", "query"],
        ["telemetry", "summary"],
        ["telemetry", "init"],
    ):
        result = runner.invoke(app, args)
        assert "SDD_COMPLIANCE_EVENTS_PATH" in result.output, args
        assert "SDD_TELEMETRY_PATH" in result.output, args
