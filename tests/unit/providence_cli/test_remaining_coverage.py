"""Coverage tests for remaining CLI helpers."""

from __future__ import annotations

import io
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from providence_cli.commands import plugin as plugin_mod
from providence_cli.commands import test as test_mod
from providence_cli.services import ask_dossier as ask_dossier_mod

runner = CliRunner()


class TestPluginCoverage:
    def test_load_registry_missing_and_invalid(self, tmp_path: Path) -> None:
        assert plugin_mod._load_registry(tmp_path) == {
            "schema_version": "1.0.0",
            "plugins": [],
        }
        path = plugin_mod._registry_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not: [valid", encoding="utf-8")
        assert plugin_mod._load_registry(tmp_path) == {
            "schema_version": "1.0.0",
            "plugins": [],
        }

    def test_list_plugins_empty_and_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(plugin_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(plugin_mod, "_ctx_json", lambda: False)
        result = runner.invoke(plugin_mod.app, ["list"])
        assert result.exit_code == 0
        assert "No plugins registered." in result.output

        payloads: list[dict[str, object]] = []
        monkeypatch.setattr(plugin_mod, "_ctx_json", lambda: True)
        monkeypatch.setattr(plugin_mod, "emit_json", payloads.append)
        result = runner.invoke(plugin_mod.app, ["list", "--json"])
        assert result.exit_code == 0
        assert payloads[0]["command"] == "plugin list"

        payloads.clear()
        plugin_mod.list_plugins(json_output=True)
        assert payloads[0]["command"] == "plugin list"

    def test_list_plugins_missing_workspace_and_plain_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(plugin_mod, "resolve_workspace_root", lambda: None)
        result = runner.invoke(plugin_mod.app, ["list"])
        assert result.exit_code != 0

        plugin_dir = tmp_path / ".providence" / "plugins"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "registry.yaml").write_text(
            "schema_version: '1.0.0'\nplugins:\n- id: one\n  type: analysis_orchestrator\n  version: '1.0.0'\n  status: active\n  entrypoint: /one\n  contract: contract\n  sdd_injection:\n    base_path: .providence/analysis\n    execution_provider: sdd-ask\n    approval_gate: required\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(plugin_mod, "resolve_workspace_root", lambda: tmp_path)
        result = runner.invoke(plugin_mod.app, ["list"])
        assert result.exit_code == 0
        assert "ID" in result.output
        assert "one" in result.output

    def test_validate_missing_and_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(plugin_mod, "resolve_workspace_root", lambda: tmp_path)
        monkeypatch.setattr(plugin_mod, "_ctx_json", lambda: False)
        result = runner.invoke(plugin_mod.app, ["validate", "missing"])
        assert result.exit_code != 0

        payloads: list[dict[str, object]] = []
        monkeypatch.setattr(plugin_mod, "_ctx_json", lambda: True)
        monkeypatch.setattr(plugin_mod, "emit_json", payloads.append)
        result = runner.invoke(plugin_mod.app, ["validate", "missing", "--json"])
        assert result.exit_code != 0
        assert payloads[0]["error"]["code"] == "plugin_not_found"

        payloads.clear()
        with pytest.raises(typer.Exit):
            plugin_mod.validate_plugin(plugin_id="missing", json_output=True)
        assert payloads[0]["error"]["code"] == "plugin_not_found"

    def test_validate_pass_and_fail_branches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plugin_dir = tmp_path / ".providence" / "plugins"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "registry.yaml").write_text(
            "schema_version: '1.0.0'\nplugins:\n- id: ok\n  type: analysis_orchestrator\n  version: '1.0.0'\n  status: active\n  entrypoint: /ok\n  contract: contract\n  sdd_injection:\n    base_path: .providence/analysis\n    execution_provider: sdd-ask\n    approval_gate: required\n- id: bad\n  type: unknown\n  version: '1.0.0'\n  status: active\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(plugin_mod, "resolve_workspace_root", lambda: tmp_path)
        result = runner.invoke(plugin_mod.app, ["validate", "ok"])
        assert result.exit_code == 0
        result = runner.invoke(plugin_mod.app, ["validate", "bad"])
        assert result.exit_code != 0

    def test_helper_branches_direct(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(plugin_mod, "_ctx_json", lambda: True)
        payloads: list[dict[str, object]] = []
        monkeypatch.setattr(plugin_mod, "emit_json", payloads.append)
        monkeypatch.setattr(plugin_mod, "resolve_workspace_root", lambda: tmp_path)
        plugin_mod.list_plugins(json_output=False)
        assert payloads[0]["command"] == "plugin list"

        entry = {
            "id": "bad",
            "type": "unknown",
            "version": "1.0.0",
            "status": "active",
        }
        assert any(
            "unknown_plugin_type" in v for v in plugin_mod._validate_entry(entry)
        )
        assert any(
            "missing sdd_injection field" in v
            for v in plugin_mod._validate_entry(
                {
                    "id": "ok",
                    "type": "analysis_orchestrator",
                    "version": "1.0.0",
                    "status": "active",
                    "entrypoint": "/ok",
                    "contract": "contract",
                    "sdd_injection": {"base_path": ".providence/analysis"},
                }
            )
        )


class TestAskDossierCoverage:
    def test_handle_budget_and_artifact_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _Logger:
            def __init__(self) -> None:
                self.debug_calls: list[tuple[object, ...]] = []

            def debug(self, *args: object) -> None:
                self.debug_calls.append(args)

        class _Typer:
            def __init__(self) -> None:
                self.messages: list[tuple[tuple[object, ...], dict[str, object]]] = []

            def echo(self, *args: object, **kwargs: object) -> None:
                self.messages.append((args, kwargs))

        logger = _Logger()
        typer_mod = _Typer()
        ask_dossier_mod.handle_dossier_error(
            Exception("x"), logger=logger, typer_module=typer_mod
        )
        assert logger.debug_calls

        class _BudgetBreach(Exception):
            pass

        fake_root = types.ModuleType("providence_runtime")
        fake_context = types.ModuleType("providence_runtime.context")
        fake_context.BudgetBreachError = _BudgetBreach
        fake_root.context = fake_context
        monkeypatch.setitem(sys.modules, "providence_runtime", fake_root)
        monkeypatch.setitem(sys.modules, "providence_runtime.context", fake_context)
        with pytest.raises(SystemExit):
            ask_dossier_mod.handle_dossier_error(
                _BudgetBreach("limit"), logger=logger, typer_module=typer_mod
            )

        assert ask_dossier_mod.resolve_dossier_budget(33) == 33

    def test_load_dossier_artifact_branches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        compiled_dir = tmp_path / ".providence" / "compiled"

        loaded: list[Path] = []

        class _CompiledArtifact:
            @staticmethod
            def from_governance_json(path: Path) -> object:
                loaded.append(path)
                return {"artifact": path.name}

        fake_artifacts = types.ModuleType("providence_runtime.artifacts")
        fake_artifacts.CompiledArtifact = _CompiledArtifact
        monkeypatch.setitem(sys.modules, "providence_runtime.artifacts", fake_artifacts)

        assert (
            ask_dossier_mod.load_dossier_artifact(
                tmp_path, compiled_active_dir_fn=lambda root: compiled_dir
            )
            is None
        )
        assert loaded == []

        compiled_dir.mkdir(parents=True)
        compiled_path = compiled_dir / "governance-core.json"
        compiled_path.write_text("{}", encoding="utf-8")
        assert ask_dossier_mod.load_dossier_artifact(
            tmp_path, compiled_active_dir_fn=lambda root: compiled_dir
        ) == {"artifact": "governance-core.json"}
        assert loaded == [compiled_path]

        class _BrokenCompiledArtifact:
            @staticmethod
            def from_governance_json(path: Path) -> object:
                raise ValueError("broken")

        fake_artifacts.CompiledArtifact = _BrokenCompiledArtifact
        assert (
            ask_dossier_mod.load_dossier_artifact(
                tmp_path, compiled_active_dir_fn=lambda root: compiled_dir
            )
            is None
        )

    def test_build_lines_and_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _ContextResult:
            matched = 2
            compression_ratio = 1.5
            items = ["- item 1", "- item 2"]
            bytes_loaded = 0

        lines = ask_dossier_mod.build_dossier_lines(
            query="q",
            skill="s",
            budget=100,
            mandates_count=3,
            budget_utilization_pct=50.0,
            context_result=_ContextResult(),
        )
        assert any("Task Query" in line for line in lines)

        class _Loader:
            def load_result(self, request: object) -> _ContextResult:
                return _ContextResult()

        fake_root = types.ModuleType("providence_runtime")
        fake_context = types.ModuleType("providence_runtime.context")
        fake_context.ContextLoader = lambda: _Loader()
        fake_context.ContextRequest = lambda **kwargs: kwargs
        fake_root.context = fake_context
        monkeypatch.setitem(sys.modules, "providence_runtime", fake_root)
        monkeypatch.setitem(sys.modules, "providence_runtime.context", fake_context)

        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        artifact = compiled_dir / "governance-core.json"
        artifact.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(
            ask_dossier_mod,
            "load_dossier_artifact",
            lambda workspace_root, compiled_active_dir_fn: object(),
        )
        out = io.StringIO()
        typer_mod = types.SimpleNamespace(echo=lambda s="", **kw: print(s, file=out))
        ask_dossier_mod.build_and_output_dossier(
            query="q",
            skill=None,
            budget=None,
            mandates_count=1,
            workspace_root=tmp_path,
            resolve_workspace_root_fn=lambda: tmp_path,
            compiled_active_dir_fn=lambda root: compiled_dir,
            logger=MagicMock(),
            typer_module=typer_mod,
        )
        assert "DOSSIER" in out.getvalue()

    def test_build_and_output_dossier_handles_loader_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _Logger:
            def __init__(self) -> None:
                self.debug_calls: list[tuple[object, ...]] = []

            def debug(self, *args: object) -> None:
                self.debug_calls.append(args)

        class _Typer:
            def __init__(self) -> None:
                self.messages: list[tuple[tuple[object, ...], dict[str, object]]] = []

            def echo(self, *args: object, **kwargs: object) -> None:
                self.messages.append((args, kwargs))

        class _Loader:
            def load_result(self, request: object) -> object:
                raise RuntimeError("loader failed")

        class _BudgetBreachError(Exception):
            pass

        fake_root = types.ModuleType("providence_runtime")
        fake_context = types.ModuleType("providence_runtime.context")
        fake_context.BudgetBreachError = _BudgetBreachError
        fake_context.ContextLoader = lambda: _Loader()
        fake_context.ContextRequest = lambda **kwargs: kwargs
        fake_root.context = fake_context
        monkeypatch.setitem(sys.modules, "providence_runtime", fake_root)
        monkeypatch.setitem(sys.modules, "providence_runtime.context", fake_context)

        logger = _Logger()
        typer_mod = _Typer()
        ask_dossier_mod.build_and_output_dossier(
            query="q",
            skill=None,
            budget=None,
            mandates_count=1,
            workspace_root=tmp_path,
            resolve_workspace_root_fn=lambda: tmp_path,
            compiled_active_dir_fn=lambda root: tmp_path,
            logger=logger,
            typer_module=typer_mod,
        )
        assert logger.debug_calls
        assert typer_mod.messages


class TestTestCommandCoverage:
    def test_import_helper_and_script_branches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert test_mod._check_import("json") is True
        assert test_mod._check_import("nonexistent_module_123") is False

        script = tmp_path / "script.py"
        script.write_text("print('ok')", encoding="utf-8")

        class _Runner:
            def run(self, cmd: list[str], cwd: str, env: dict[str, str]) -> MagicMock:
                return MagicMock(returncode=0)

        with patch(
            "providence_core.utils.process.SafeProcessRunner", lambda: _Runner()
        ):
            assert test_mod._run_script(str(script), ["--x"], str(tmp_path)) == 0
            assert test_mod._run_cli(["runtime", "status"], str(tmp_path)) == 0
            assert test_mod._run_pytest(["-q"], str(tmp_path)) == 0

    def test_ci_validate_failure_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path
        for sub in ("tools/health", "tools/governance", "tools/testing"):
            (root / sub).mkdir(parents=True, exist_ok=True)
        (root / "tools" / "health" / "health_check.py").write_text("", encoding="utf-8")
        (root / "tools" / "governance" / "compliance.py").write_text(
            "", encoding="utf-8"
        )
        (root / "tools" / "testing" / "run-all-tests.py").write_text(
            "", encoding="utf-8"
        )
        monkeypatch.setattr(test_mod, "detect_repo_root", lambda: root)
        monkeypatch.setattr(test_mod, "_check_import", lambda module: module != "rich")
        monkeypatch.setattr(test_mod, "_run_script", lambda *args, **kwargs: 0)
        monkeypatch.setattr(test_mod, "_run_cli", lambda *args, **kwargs: 0)
        monkeypatch.setattr(test_mod, "_run_pytest", lambda *args, **kwargs: 0)
        with pytest.raises(typer.Exit):
            test_mod.ci_validate(
                health=True, governance=True, tests=True, soak_threads=False
            )
