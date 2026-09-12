from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from providence_wizard.orchestration._phase456_run import run_phase456_pipeline


def _make_generator(tmp_path: Path) -> tuple[SimpleNamespace, list[str]]:
    messages: list[str] = []
    generator = SimpleNamespace(
        governance_core_path=tmp_path / "core.json",
        governance_client=tmp_path / "client.json",
        verbose=False,
        dir=tmp_path / ".providence",
        repo_root=tmp_path,
        runtime_dir=tmp_path / ".providence" / "runtime",
        output_base=tmp_path,
        config={"language": "Python"},
        selected_seedlings=None,
        _emit=messages.append,
        _write_sources=lambda *args: True,
        _generate_seedlings=lambda *args: True,
        _generate_prompt_submit_hooks=lambda *args: True,
    )
    return generator, messages


def test_run_phase456_pipeline_returns_loader_errors(
    tmp_path: Path, monkeypatch
) -> None:
    generator, _ = _make_generator(tmp_path)
    expected = {
        "success": False,
        "phase": "Phase 4-6",
        "output_path": str(tmp_path / ".providence"),
        "mandates": 0,
        "guidelines": 0,
        "categories": [],
        "errors": ["Failed to load governance"],
    }
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._load_governance",
        lambda *args: ([], {}, {}, expected),
    )

    assert run_phase456_pipeline(generator) == expected


def test_run_phase456_pipeline_stops_when_source_write_fails(
    tmp_path: Path, monkeypatch
) -> None:
    generator, _ = _make_generator(tmp_path)
    generator._write_sources = lambda *args: False
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._load_governance",
        lambda *args: ([{"id": "M001"}], {"G001": {}}, {"core": [{}]}, {"errors": []}),
    )

    result = run_phase456_pipeline(generator)

    assert result.get("success", False) is False
    assert result["mandates"] == 1
    assert result["guidelines"] == 1
    assert result["categories"] == ["core"]


def test_run_phase456_pipeline_adds_metadata_error_when_compile_fails(
    tmp_path: Path, monkeypatch
) -> None:
    generator, _ = _make_generator(tmp_path)
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._load_governance",
        lambda *args: ([{"id": "M001"}], {"G001": {}}, {"core": [{}]}, {"errors": []}),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._compile_artifacts",
        lambda *args: (False, object()),
    )

    result = run_phase456_pipeline(generator)

    assert result["errors"] == ["Failed to generate metadata"]


def test_run_phase456_pipeline_returns_when_ide_deploy_fails(
    tmp_path: Path, monkeypatch
) -> None:
    generator, _ = _make_generator(tmp_path)
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._load_governance",
        lambda *args: ([{"id": "M001"}], {"G001": {}}, {"core": [{}]}, {"errors": []}),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._compile_artifacts",
        lambda *args: (True, object()),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._deploy_ide_templates",
        lambda *args: False,
    )

    result = run_phase456_pipeline(generator)

    assert result.get("success", False) is False


def test_run_phase456_pipeline_returns_when_seedling_generation_fails(
    tmp_path: Path, monkeypatch
) -> None:
    generator, _ = _make_generator(tmp_path)
    generator._generate_seedlings = lambda *args: False
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._load_governance",
        lambda *args: ([{"id": "M001"}], {"G001": {}}, {"core": [{}]}, {"errors": []}),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._compile_artifacts",
        lambda *args: (True, object()),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._deploy_ide_templates",
        lambda *args: True,
    )

    result = run_phase456_pipeline(generator)

    assert result.get("success", False) is False


def test_run_phase456_pipeline_returns_when_prompt_hook_generation_fails(
    tmp_path: Path, monkeypatch
) -> None:
    generator, _ = _make_generator(tmp_path)
    generator._generate_prompt_submit_hooks = lambda *args: False
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._load_governance",
        lambda *args: ([{"id": "M001"}], {"G001": {}}, {"core": [{}]}, {"errors": []}),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._compile_artifacts",
        lambda *args: (True, object()),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._deploy_ide_templates",
        lambda *args: True,
    )

    result = run_phase456_pipeline(generator)

    assert result.get("success", False) is False


def test_run_phase456_pipeline_success_path_emits_summary(
    tmp_path: Path, monkeypatch
) -> None:
    generator, messages = _make_generator(tmp_path)
    compiler = SimpleNamespace(
        governance_fingerprint="fp",
        generated_at="2026-01-01T00:00:00",
        mandates=[{"id": "M001"}],
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._load_governance",
        lambda *args: (
            [{"id": "M001"}],
            {"G001": {"id": "G001"}},
            {"core": [{"id": "G001"}]},
            {"errors": [], "output_path": str(tmp_path / ".providence")},
        ),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._compile_artifacts",
        lambda *args: (True, compiler),
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._deploy_ide_templates",
        lambda *args: True,
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._generate_adapters",
        lambda *args: None,
    )
    monkeypatch.setattr(
        "providence_wizard.orchestration._phase456_run._validate_output",
        lambda *args: True,
    )

    result = run_phase456_pipeline(generator)

    assert result["success"] is True
    assert any("phase4...OK" in message for message in messages)
    assert any("location...OK" in message for message in messages)
