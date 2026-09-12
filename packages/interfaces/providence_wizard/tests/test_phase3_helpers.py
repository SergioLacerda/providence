from __future__ import annotations

import json
from pathlib import Path

from providence_wizard.orchestration.wizard import _phase3_helpers as helpers


def test_copy_seedlings_returns_true_when_template_source_missing(
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    assert helpers._copy_seedlings(tmp_path, tmp_path / "out", messages.append) is True
    assert messages == []


def test_copy_seedlings_copies_supported_directories(tmp_path: Path) -> None:
    source_base = (
        tmp_path
        / "packages"
        / "features"
        / "providence_integration"
        / "src"
        / "providence_integration"
        / "templates"
    )
    (source_base / ".github").mkdir(parents=True)
    (source_base / ".github" / "copilot.md").write_text("x", encoding="utf-8")
    (source_base / ".vscode").mkdir(parents=True)
    (source_base / ".vscode" / "ai-rules.md").write_text("y", encoding="utf-8")
    (source_base / ".cursor" / "rules").mkdir(parents=True)
    (source_base / ".cursor" / "rules" / "spec.mdc").write_text("z", encoding="utf-8")

    output_path = tmp_path / "out"

    assert helpers._copy_seedlings(tmp_path, output_path, lambda _msg: None) is True
    assert (output_path / ".github" / "copilot.md").read_text(encoding="utf-8") == "x"
    assert (output_path / ".vscode" / "ai-rules.md").read_text(encoding="utf-8") == "y"
    assert (output_path / ".cursor" / "rules" / "spec.mdc").read_text(
        encoding="utf-8"
    ) == "z"


def test_copy_seedlings_reports_error_when_copy_fails(
    tmp_path: Path, monkeypatch
) -> None:
    source_base = (
        tmp_path
        / "packages"
        / "features"
        / "providence_integration"
        / "src"
        / "providence_integration"
        / "templates"
        / ".github"
    )
    source_base.mkdir(parents=True)
    (source_base / "copilot.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(
        "providence_wizard.orchestration.wizard._phase3_helpers.shutil.copy2",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("copy failed")),
    )
    messages: list[str] = []

    assert helpers._copy_seedlings(tmp_path, tmp_path / "out", messages.append) is False
    assert any("Error copying seedlings" in message for message in messages)


def test_generate_spec_file_skips_when_canonical_dir_missing(tmp_path: Path) -> None:
    messages: list[str] = []
    helpers._generate_spec_file(tmp_path, tmp_path / "out", messages.append)
    assert messages == []


def test_generate_spec_file_emits_success(tmp_path: Path, monkeypatch) -> None:
    canonical_dir = tmp_path / "docs" / "spec" / "canonical" / "core" / "mandates"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "M001.md").write_text("# Mandate", encoding="utf-8")

    class _FakeBuilder:
        @staticmethod
        def generate_spec_file(**kwargs):
            output_path = kwargs["output_path"]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("{}", encoding="utf-8")
            return {"mandates_written": 1}

    monkeypatch.setattr(
        "providence_integration.builders.governance.pipeline_builder.PipelineBuilder",
        _FakeBuilder,
    )
    messages: list[str] = []

    helpers._generate_spec_file(tmp_path, tmp_path / "out", messages.append)

    assert any("Spec file" in message for message in messages)


def test_generate_spec_file_reports_skip_when_builder_fails(
    tmp_path: Path, monkeypatch
) -> None:
    canonical_dir = tmp_path / "docs" / "spec" / "canonical" / "core" / "mandates"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "M001.md").write_text("# Mandate", encoding="utf-8")

    class _FakeBuilder:
        @staticmethod
        def generate_spec_file(**_kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "providence_integration.builders.governance.pipeline_builder.PipelineBuilder",
        _FakeBuilder,
    )
    messages: list[str] = []

    helpers._generate_spec_file(tmp_path, tmp_path / "out", messages.append)

    assert any("generation skipped" in message for message in messages)


def test_generate_source_files_returns_specific_errors(
    monkeypatch, tmp_path: Path
) -> None:
    class _FailMandates:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def write(self, _mandates):
            return False

    monkeypatch.setattr(
        "providence_wizard.orchestration.wizard._phase3_helpers.MandatesCompiler",
        _FailMandates,
    )
    assert (
        helpers._generate_source_files(tmp_path, "Python", lambda _msg: None, [], [])
        == "Failed to generate mandates.md"
    )


def test_generate_source_files_returns_guidelines_error(
    monkeypatch, tmp_path: Path
) -> None:
    class _OkMandates:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def write(self, _mandates):
            return True

    class _FailGuidelines:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def write(self, _guidelines):
            return False

    monkeypatch.setattr(
        "providence_wizard.orchestration.wizard._phase3_helpers.MandatesCompiler",
        _OkMandates,
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration.wizard._phase3_helpers.GuidelinesCompiler",
        _FailGuidelines,
    )
    assert (
        helpers._generate_source_files(tmp_path, "Python", lambda _msg: None, [], [])
        == "Failed to generate guidelines files"
    )


def test_generate_source_files_returns_readme_error(
    monkeypatch, tmp_path: Path
) -> None:
    class _OkCompiler:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def write(self, *_args, **_kwargs):
            return True

    class _FailReadme(_OkCompiler):
        def write(self, *_args, **_kwargs):
            return False

    monkeypatch.setattr(
        "providence_wizard.orchestration.wizard._phase3_helpers.MandatesCompiler",
        _OkCompiler,
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration.wizard._phase3_helpers.GuidelinesCompiler",
        _OkCompiler,
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration.wizard._phase3_helpers.SourceReadmeCompiler",
        _FailReadme,
    )
    assert (
        helpers._generate_source_files(tmp_path, "Python", lambda _msg: None, [], [])
        == "Failed to generate source README"
    )


def test_load_compiled_governance_reads_mandates_and_guidelines(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "governance-core.json").write_text(
        json.dumps({"items": [{"id": "M001", "type": "MANDATE"}]}), encoding="utf-8"
    )
    (source_dir / "governance-client.json").write_text(
        json.dumps({"items": [{"id": "G001", "type": "GUIDELINE"}]}), encoding="utf-8"
    )

    mandates, guidelines = helpers._load_compiled_governance(
        tmp_path, lambda _msg: None
    )

    assert mandates == [{"id": "M001", "type": "MANDATE"}]
    assert guidelines == [{"id": "G001", "type": "GUIDELINE"}]


def test_load_compiled_governance_reports_error_for_invalid_json(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "governance-core.json").write_text("{bad json", encoding="utf-8")
    messages: list[str] = []

    mandates, guidelines = helpers._load_compiled_governance(tmp_path, messages.append)

    assert mandates == []
    assert guidelines == []
    assert any("Error loading compiled governance" in message for message in messages)
