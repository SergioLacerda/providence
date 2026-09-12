from __future__ import annotations

from pathlib import Path
from typing import Any

from providence_wizard.orchestration._phase456_pipeline_steps import (
    _compile_artifacts,
    _deploy_ide_templates,
    _generate_adapters,
    _generate_plugin_workspace_dirs,
    _validate_output,
)


class _FakeCompiler:
    def __init__(self, *, compile_ok: bool, metadata_ok: bool, **_: Any) -> None:
        self._compile_ok = compile_ok
        self._metadata_ok = metadata_ok

    def compile_artifacts(self) -> bool:
        return self._compile_ok

    def generate_metadata(self) -> bool:
        return self._metadata_ok


def test_compile_artifacts_emits_warning_when_compile_fails_verbose(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.ArtifactCompiler",
        lambda **kwargs: _FakeCompiler(compile_ok=False, metadata_ok=True, **kwargs),
    )
    messages: list[str] = []

    success, _compiler = _compile_artifacts(
        repo_root=tmp_path,
        sdd_dir=tmp_path,
        runtime_dir=tmp_path,
        mandates=[],
        guidelines={},
        guidelines_by_category={},
        config={},
        verbose=True,
        emit=messages.append,
    )

    assert success is True
    assert any("Artifact compilation skipped" in message for message in messages)


def test_compile_artifacts_returns_false_when_metadata_generation_fails(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.ArtifactCompiler",
        lambda **kwargs: _FakeCompiler(compile_ok=True, metadata_ok=False, **kwargs),
    )

    success, _compiler = _compile_artifacts(
        repo_root=tmp_path,
        sdd_dir=tmp_path,
        runtime_dir=tmp_path,
        mandates=[],
        guidelines={},
        guidelines_by_category={},
        config={},
        verbose=False,
        emit=lambda _msg: None,
    )

    assert success is False


class _FakeTemplateDeployer:
    def __init__(self, *, copy_ok: bool, ide_ok: bool, **_: Any) -> None:
        self._copy_ok = copy_ok
        self._ide_ok = ide_ok

    def copy_templates(self) -> bool:
        return self._copy_ok

    def create_ide_templates(self) -> bool:
        return self._ide_ok


class _FakeSeedlingInjector:
    def __init__(self, **_: Any) -> None:
        pass

    def inject_bootstrap_metadata(self, **_: Any) -> None:
        pass

    def populate_ide_rules(self, **_: Any) -> None:
        pass


class _FakeArtifactCompiler:
    """Stand-in for ArtifactCompiler exposing only what GovernanceInstallSnapshot reads."""

    def __init__(self) -> None:
        self.mandates = [{"id": "M001", "title": "Clean Architecture"}]
        self.guidelines: dict[str, Any] = {}
        self.guidelines_by_category: dict[str, Any] = {}
        self.governance_fingerprint = "abc12345"
        self.generated_at = "2026-07-04T00:00:00Z"


class _RecordingSeedlingInjector:
    def __init__(self, **_: Any) -> None:
        self.bootstrap_calls: list[dict[str, Any]] = []
        self.ide_rules_calls: list[dict[str, Any]] = []

    def inject_bootstrap_metadata(self, **kwargs: Any) -> None:
        self.bootstrap_calls.append(kwargs)

    def populate_ide_rules(self, **kwargs: Any) -> None:
        self.ide_rules_calls.append(kwargs)


def test_deploy_ide_templates_returns_false_when_copy_templates_fails(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.TemplateDeployer",
        lambda **kwargs: _FakeTemplateDeployer(copy_ok=False, ide_ok=True, **kwargs),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.SeedlingInjector",
        _FakeSeedlingInjector,
    )
    result: dict[str, Any] = {"errors": []}

    success = _deploy_ide_templates(
        repo_root=tmp_path,
        output_base=tmp_path,
        config={},
        verbose=False,
        compiler=object(),
        result=result,  # type: ignore[arg-type]
    )

    assert success is False
    assert result["errors"] == ["Failed to copy templates"]


def test_deploy_ide_templates_returns_false_when_create_ide_templates_fails(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.TemplateDeployer",
        lambda **kwargs: _FakeTemplateDeployer(copy_ok=True, ide_ok=False, **kwargs),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.SeedlingInjector",
        _FakeSeedlingInjector,
    )
    result: dict[str, Any] = {"errors": []}

    success = _deploy_ide_templates(
        repo_root=tmp_path,
        output_base=tmp_path,
        config={},
        verbose=False,
        compiler=object(),
        result=result,  # type: ignore[arg-type]
    )

    assert success is False
    assert result["errors"] == ["Failed to copy configuration templates"]


def test_deploy_ide_templates_sources_injector_args_from_snapshot(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Behavior-preserving check: snapshot-sourced args match the compiler's raw attributes."""
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.TemplateDeployer",
        lambda **kwargs: _FakeTemplateDeployer(copy_ok=True, ide_ok=True, **kwargs),
    )
    injectors: list[_RecordingSeedlingInjector] = []

    def _make_injector(**kwargs: Any) -> _RecordingSeedlingInjector:
        injector = _RecordingSeedlingInjector(**kwargs)
        injectors.append(injector)
        return injector

    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.SeedlingInjector",
        _make_injector,
    )
    compiler = _FakeArtifactCompiler()
    result: dict[str, Any] = {"errors": []}

    success = _deploy_ide_templates(
        repo_root=tmp_path,
        output_base=tmp_path,
        config={},
        verbose=False,
        compiler=compiler,
        result=result,  # type: ignore[arg-type]
    )

    assert success is True
    injector = injectors[0]
    assert injector.bootstrap_calls == [
        {
            "fingerprint": compiler.governance_fingerprint,
            "generated_at": compiler.generated_at,
            "mandates_count": len(compiler.mandates),
        }
    ]
    assert injector.ide_rules_calls == [
        {"mandates": compiler.mandates, "fingerprint": compiler.governance_fingerprint}
    ]


class _FakeValidator:
    def __init__(self, **_: Any) -> None:
        pass

    def validate(self) -> tuple[bool, dict[str, Any]]:
        return False, {"errors": ["bad output"], "checks": {}}


def test_validate_output_extends_errors_and_returns_false(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.OutputValidator",
        _FakeValidator,
    )
    result: dict[str, Any] = {"errors": []}

    success = _validate_output(
        output_base=tmp_path,
        guidelines_by_category={},
        config={},
        verbose=False,
        emit=lambda _msg: None,
        result=result,  # type: ignore[arg-type]
    )

    assert success is False
    assert result["errors"] == ["bad output"]


def test_generate_plugin_workspace_dirs_returns_false_on_error(
    monkeypatch: Any, tmp_path: Path
) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "providence_cli.generators._plugins.generate_plugins_registry", boom
    )

    assert _generate_plugin_workspace_dirs(tmp_path, {}) is False


class _FakeAdapterResult:
    def __init__(self, success: bool) -> None:
        self.success = success
        self.files_written: list[str] = []
        self.errors: list[str] = ["bad adapter"]


class _FakeAdapterGenerator:
    def __init__(self, results: dict[str, _FakeAdapterResult]) -> None:
        self._results = results

    def generate(self, output_dir: Path) -> dict[str, _FakeAdapterResult]:
        return self._results


def test_generate_adapters_emits_warning_when_adapter_fails(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.AdapterGenerator",
        lambda: _FakeAdapterGenerator({"claude": _FakeAdapterResult(success=False)}),
    )
    messages: list[str] = []

    _generate_adapters(tmp_path, messages.append)

    assert messages == ["adapters...WARN (claude)"]


def test_generate_adapters_emits_detailed_warning_when_debug(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.AdapterGenerator",
        lambda: _FakeAdapterGenerator({"claude": _FakeAdapterResult(success=False)}),
    )
    messages: list[str] = []

    _generate_adapters(tmp_path, messages.append, verbose=True)

    assert any("had errors" in message for message in messages)
    assert any("adapters...WARN (claude)" in message for message in messages)


def test_generate_adapters_emits_warning_on_exception(
    monkeypatch: Any, tmp_path: Path
) -> None:
    def boom() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.AdapterGenerator",
        boom,
    )
    messages: list[str] = []

    _generate_adapters(tmp_path, messages.append)

    assert messages == ["adapters...WARN"]


def test_generate_adapters_emits_detailed_exception_when_debug(
    monkeypatch: Any, tmp_path: Path
) -> None:
    def boom() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_pipeline_steps.AdapterGenerator",
        boom,
    )
    messages: list[str] = []

    _generate_adapters(tmp_path, messages.append, verbose=True)

    assert any("non-critical" in message for message in messages)
    assert any("adapters...WARN" in message for message in messages)
