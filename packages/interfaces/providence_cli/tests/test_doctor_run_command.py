"""Coverage tests for the `providence doctor run` command branches."""

from __future__ import annotations

import builtins
import sys
import types
from pathlib import Path

import pytest
from typer.testing import CliRunner

from providence_cli.commands import doctor as doctor_mod
from providence_cli.commands.doctor import app as doctor_app

runner = CliRunner()


def _fake_doctor_integration_engine(report_score: int = 100):
    class _FakeReport:
        def pretty(self) -> str:
            return "pretty-report"

        def score(self) -> int:
            return report_score

    class _FakeEngine:
        def __init__(
            self, spec: str, context_overrides: dict[str, object] | None = None
        ):
            self.spec = spec
            self.context_overrides = context_overrides

        def run(self) -> _FakeReport:
            return _FakeReport()

    return _FakeEngine


def _install_fake_integration_engine(
    monkeypatch: pytest.MonkeyPatch, engine_cls: type[object]
) -> None:
    root_mod = types.ModuleType("providence_integration")
    engine_pkg = types.ModuleType("providence_integration.engine")
    engine_mod = types.ModuleType("providence_integration.engine.integration_engine")
    engine_mod.IntegrationEngine = engine_cls
    root_mod.engine = engine_pkg
    engine_pkg.integration_engine = engine_mod
    monkeypatch.setitem(sys.modules, "providence_integration", root_mod)
    monkeypatch.setitem(sys.modules, "providence_integration.engine", engine_pkg)
    monkeypatch.setitem(
        sys.modules, "providence_integration.engine.integration_engine", engine_mod
    )


class TestDoctorRun:
    def test_callback_lists_commands_without_subcommand(self) -> None:
        result = runner.invoke(doctor_app, [])
        assert result.exit_code == 0
        assert "Doctor commands:" in result.output
        assert "run" in result.output

    def test_run_import_error_branch(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        real_import = builtins.__import__

        def _blocked_import(name: str, globals=None, locals=None, fromlist=(), level=0):
            if name.startswith("providence_integration"):
                raise ImportError("blocked for test")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", _blocked_import)
        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )
        result = runner.invoke(
            doctor_app, ["run", "--spec", str(tmp_path / "spec.yaml")]
        )
        assert result.exit_code != 0
        assert "unavailable because optional dependency" in result.output

    def test_run_missing_spec_branch(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        spec = tmp_path / "spec.yaml"
        monkeypatch.setattr(doctor_mod, "_get_default_spec", lambda: spec)
        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )

        fake_engine = _fake_doctor_integration_engine(report_score=100)
        _install_fake_integration_engine(monkeypatch, fake_engine)
        result = runner.invoke(doctor_app, ["run"])

        assert result.exit_code != 0
        assert "Spec file not found" in result.output

    def test_run_real_mode_and_failure_score(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        spec = tmp_path / "spec.yaml"
        spec.write_text("spec", encoding="utf-8")
        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )

        fake_engine = _fake_doctor_integration_engine(report_score=99)
        _install_fake_integration_engine(monkeypatch, fake_engine)
        monkeypatch.setattr(doctor_mod, "detect_repo_root", lambda: tmp_path)
        result = runner.invoke(
            doctor_app, ["run", "--spec", str(spec), "--mode", "real"]
        )

        assert result.exit_code != 0
        assert "Next: review failing checks above" in result.output

    def test_run_success_branch(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        spec = tmp_path / "spec.yaml"
        spec.write_text("spec", encoding="utf-8")
        monkeypatch.setattr(doctor_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(
            doctor_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )
        monkeypatch.setattr(doctor_mod, "detect_repo_root", lambda: tmp_path)

        fake_engine = _fake_doctor_integration_engine(report_score=100)
        _install_fake_integration_engine(monkeypatch, fake_engine)
        result = runner.invoke(doctor_app, ["run", "--spec", str(spec)])

        assert result.exit_code == 0
        assert "pretty-report" in result.output
