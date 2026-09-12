from __future__ import annotations

from pathlib import Path

import pytest

from providence_wizard.orchestration.wizard.phase3_compiler import Phase3Compiler


class _FakePipelineBuilder:
    """Minimal stub matching PipelineBuilder API used by Phase3Compiler."""

    def __init__(
        self,
        spec_path: str,
        parsed_items: dict[str, list[dict[str, str]]] | None = None,
    ) -> None:
        self.spec_path = spec_path
        self.parsed_items = parsed_items or {"mandates": [], "guidelines": []}

    def build(self) -> dict[str, object]:
        return {
            "governance_core": {"fingerprint": "core", "version": "3.0"},
            "governance_client": {
                "fingerprint": "client",
                "version": "3.0",
                "fingerprint_core_salt": "core",
            },
            "core_items": [{"id": "M001", "type": "MANDATE"}],
            "client_items": [{"id": "G001", "type": "GUIDELINE"}],
        }

    def save_outputs(self, output_dir: str) -> dict[str, str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "governance-core.json").write_text(
            '{"category":"CORE","version":"3.0","fingerprint":"core","items":[{"id":"M001","type":"MANDATE"}]}',
            encoding="utf-8",
        )
        (out / "governance-client.json").write_text(
            '{"category":"CLIENT","version":"3.0","fingerprint":"client","fingerprint_core_salt":"core","items":[{"id":"G001","type":"GUIDELINE"}]}',
            encoding="utf-8",
        )
        return {
            "governance_core": str(out / "governance-core.json"),
            "governance_client": str(out / "governance-client.json"),
        }


def _make_compiler(tmp_path: Path, language: str = "Go") -> Phase3Compiler:
    compiler = Phase3Compiler(
        markdown_input_path=tmp_path / "build" / "phase-2-input",
        output_path=tmp_path / "compiled",
        repo_root=tmp_path,
        verbose=False,
        emitter=lambda _msg: None,
    )
    compiler.language = language
    return compiler


def test_validate_template_root_returns_false_with_explicit_error(
    tmp_path: Path,
) -> None:
    compiler = _make_compiler(tmp_path)
    assert compiler.validate_template_root() is False
    assert compiler.last_error is not None
    assert "Template root not found" in compiler.last_error


def test_resolve_language_template_dir_returns_go_directory(tmp_path: Path) -> None:
    template_dir = (
        tmp_path
        / "packages"
        / "interfaces"
        / "providence_wizard"
        / "src"
        / "providence_wizard"
        / "templates"
        / "languages"
        / "go"
    )
    template_dir.mkdir(parents=True)
    (template_dir / "go.mod").write_text("module demo\n", encoding="utf-8")
    compiler = _make_compiler(tmp_path, language="Go")
    resolved = compiler.resolve_language_template_dir()
    assert resolved == template_dir


def test_phase3_uses_pipeline_builder_save_outputs_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "providence_integration.builders.governance.pipeline_builder.PipelineBuilder",
        _FakePipelineBuilder,
    )

    markdown_input = tmp_path / "generated" / "client" / "build" / "phase-2-input"
    markdown_input.mkdir(parents=True)
    output_path = tmp_path / "generated" / "client" / "compiled"

    compiler = Phase3Compiler(markdown_input, output_path, tmp_path)

    success = compiler.compile_with_pipeline_builder({"mandates": [], "guidelines": []})

    assert success is True
    assert (output_path / "source" / "governance-core.json").exists()
    assert (output_path / "source" / "governance-client.json").exists()


def test_has_staged_input_files_reports_presence_and_absence(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    assert compiler.has_staged_input_files() is False

    compiler.markdown_input_path.mkdir(parents=True)
    (compiler.markdown_input_path / "file.md").write_text("x", encoding="utf-8")
    assert compiler.has_staged_input_files() is True


def test_load_wizard_config_reads_language(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    compiler.wizard_config_path.parent.mkdir(parents=True)
    compiler.wizard_config_path.write_text('{"language": "Rust"}', encoding="utf-8")

    assert compiler.load_wizard_config() is True
    assert compiler.language == "Rust"


def test_load_wizard_config_returns_false_on_invalid_json(tmp_path: Path) -> None:
    messages: list[str] = []
    compiler = Phase3Compiler(
        markdown_input_path=tmp_path / "build" / "phase-2-input",
        output_path=tmp_path / "compiled",
        repo_root=tmp_path,
        emitter=messages.append,
    )
    compiler.wizard_config_path.parent.mkdir(parents=True)
    compiler.wizard_config_path.write_text("{bad json", encoding="utf-8")

    assert compiler.load_wizard_config() is False
    assert any("Error loading config" in message for message in messages)


def test_create_structure_returns_false_when_output_is_invalid(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    compiler.output_path.write_text("not a directory", encoding="utf-8")

    assert compiler.create_structure() is False


def test_last_error_setter_updates_locator(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)

    compiler.last_error = "boom"

    assert compiler.last_error == "boom"


def test_log_emits_only_when_verbose(tmp_path: Path) -> None:
    messages: list[str] = []
    compiler = Phase3Compiler(
        markdown_input_path=tmp_path / "build" / "phase-2-input",
        output_path=tmp_path / "compiled",
        repo_root=tmp_path,
        verbose=True,
        emitter=messages.append,
    )

    compiler.log("hello")

    assert messages == ["    hello"]


def test_parse_markdown_items_updates_selected_guidelines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    compiler = _make_compiler(tmp_path)
    monkeypatch.setattr(
        compiler._parser,
        "parse_items",
        lambda _path: {
            "mandates": [{"id": "M001"}],
            "guidelines": [{"id": "G001"}, {"id": "G002"}],
        },
    )

    items = compiler.parse_markdown_items()

    assert items["mandates"] == [{"id": "M001"}]
    assert compiler.selected_guidelines == ["G001", "G002"]


def test_compile_with_pipeline_builder_uses_fallback_docs_meta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    class _FakeBuilder:
        def __init__(self, spec_path: str, parsed_items: dict[str, object]) -> None:
            captured["spec_path"] = spec_path

        def build(self) -> None:
            return None

        def save_outputs(self, output_dir: str) -> None:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

    compiler = _make_compiler(tmp_path)
    monkeypatch.setattr(
        "providence_wizard.orchestration.wizard._phase3_helpers.get_sdd_paths",
        lambda: (_ for _ in ()).throw(RuntimeError("no env")),
    )
    monkeypatch.setattr(
        "providence_integration.builders.governance.pipeline_builder.PipelineBuilder",
        _FakeBuilder,
    )

    assert (
        compiler.compile_with_pipeline_builder({"mandates": [], "guidelines": []})
        is True
    )
    assert (
        str(tmp_path / "generated" / "client" / "build" / "docs-meta")
        == captured["spec_path"]
    )


def test_load_compiled_governance_delegates_to_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    compiler = _make_compiler(tmp_path)
    monkeypatch.setattr(
        "providence_wizard.orchestration.wizard.phase3_compiler._load_compiled_governance",
        lambda output_path, emit: ([{"id": "M001"}], [{"id": "G001"}]),
    )

    mandates, guidelines = compiler.load_compiled_governance()

    assert mandates == [{"id": "M001"}]
    assert guidelines == [{"id": "G001"}]


def test_run_returns_error_when_no_staged_files(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)

    result = compiler.run()

    assert result["success"] is False
    assert "No staged files found" in result["error"]


def test_run_returns_error_when_compile_fails(tmp_path: Path, monkeypatch) -> None:
    compiler = _make_compiler(tmp_path)
    compiler.markdown_input_path.mkdir(parents=True)
    (compiler.markdown_input_path / "input.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(compiler, "compile_with_pipeline_builder", lambda _items: False)
    monkeypatch.setattr(
        compiler,
        "parse_markdown_items",
        lambda: {"mandates": [], "guidelines": []},
    )

    result = compiler.run()

    assert result == {"success": False, "error": "Failed to compile"}


def test_run_returns_error_when_copy_seedlings_fails(
    tmp_path: Path, monkeypatch
) -> None:
    compiler = _make_compiler(tmp_path)
    compiler.markdown_input_path.mkdir(parents=True)
    (compiler.markdown_input_path / "input.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(compiler, "copy_seedlings", lambda: False)
    monkeypatch.setattr(compiler, "compile_with_pipeline_builder", lambda _items: True)
    monkeypatch.setattr(
        compiler,
        "parse_markdown_items",
        lambda: {"mandates": [], "guidelines": []},
    )

    result = compiler.run()

    assert result == {"success": False, "error": "Failed to copy seedlings"}


def test_run_returns_source_generation_error_when_helpers_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    compiler = _make_compiler(tmp_path)
    compiler.markdown_input_path.mkdir(parents=True)
    (compiler.markdown_input_path / "input.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(compiler, "compile_with_pipeline_builder", lambda _items: True)
    monkeypatch.setattr(
        compiler,
        "parse_markdown_items",
        lambda: {"mandates": [{"id": "M001"}], "guidelines": []},
    )
    monkeypatch.setattr(
        compiler,
        "load_compiled_governance",
        lambda: ([{"id": "M001"}], [{"id": "G001"}]),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration.wizard.phase3_compiler._generate_source_files",
        lambda *_args: "Failed to generate source README",
    )

    result = compiler.run()

    assert result == {"success": False, "error": "Failed to generate source README"}


def test_run_success_returns_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    messages: list[str] = []
    compiler = Phase3Compiler(
        markdown_input_path=tmp_path / "build" / "phase-2-input",
        output_path=tmp_path / "compiled",
        repo_root=tmp_path,
        emitter=messages.append,
    )
    compiler.markdown_input_path.mkdir(parents=True)
    (compiler.markdown_input_path / "input.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(
        compiler,
        "parse_markdown_items",
        lambda: {"mandates": [{"id": "M001"}], "guidelines": [{"id": "G001"}]},
    )
    monkeypatch.setattr(compiler, "compile_with_pipeline_builder", lambda _items: True)
    monkeypatch.setattr(compiler, "copy_seedlings", lambda: True)
    monkeypatch.setattr(
        compiler,
        "load_compiled_governance",
        lambda: ([{"id": "M001"}], [{"id": "G001"}]),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration.wizard.phase3_compiler._generate_source_files",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration.wizard.phase3_compiler._generate_spec_file",
        lambda *_args: None,
    )

    result = compiler.run()

    assert result["success"] is True
    assert result["mandates"] == 1
    assert result["guidelines"] == 1
    assert any("compile...OK" in message for message in messages)
