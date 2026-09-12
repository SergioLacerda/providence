from __future__ import annotations

import json
from pathlib import Path

from providence_wizard.orchestration.mandate_compiler import MandateCompiler
from providence_wizard.orchestration.phase5_artifact_compiler import ArtifactCompiler


def _make_compiler(tmp_path: Path) -> ArtifactCompiler:
    sdd_dir = tmp_path / ".providence"
    runtime_dir = sdd_dir / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return ArtifactCompiler(
        repo_root=tmp_path,
        sdd_dir=sdd_dir,
        runtime_dir=runtime_dir,
        mandates=[{"id": "M001", "title": "Mandate"}],
        guidelines={"G001": {"id": "G001"}},
        guidelines_by_category={"core": [{"id": "G001"}]},
        config={"language": "Python"},
        verbose=False,
        emitter=lambda _msg: None,
    )


def test_compile_artifacts_returns_true_without_spec_dir(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    assert compiler.compile_artifacts() is True


def test_compile_artifacts_handles_missing_spec_files(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)
    (tmp_path / "spec").mkdir()
    assert compiler.compile_artifacts() is True


def test_compile_artifacts_calls_compiler_for_existing_specs(
    tmp_path: Path, monkeypatch
) -> None:
    compiler = _make_compiler(tmp_path)
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "mandate.spec").write_text("m", encoding="utf-8")
    (spec_dir / "guidelines.dsl").write_text("g", encoding="utf-8")
    calls: list[tuple[str, str]] = []

    class _FakeCompiler:
        def __init__(self, verbose: bool = False) -> None:
            self.verbose = verbose

        def compile_mandate_spec(self, src: Path, dst: Path, format: str) -> bool:
            calls.append((src.name, format))
            return True

        def compile_guidelines_dsl(self, src: Path, dst: Path, format: str) -> bool:
            calls.append((src.name, format))
            return True

    monkeypatch.setattr(
        "providence_wizard.orchestration.mandate_compiler.MandateCompiler",
        _FakeCompiler,
    )

    assert compiler.compile_artifacts() is True
    assert ("mandate.spec", "msgpack") in calls or ("mandate.spec", "json") in calls
    assert ("guidelines.dsl", "msgpack") in calls or ("guidelines.dsl", "json") in calls


def test_compile_artifacts_swallows_compiler_exceptions(
    tmp_path: Path, monkeypatch
) -> None:
    compiler = _make_compiler(tmp_path)

    class _BoomCompiler:
        def __init__(self, verbose: bool = False) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "providence_wizard.orchestration.mandate_compiler.MandateCompiler",
        _BoomCompiler,
    )

    assert compiler.compile_artifacts() is True


def test_mandate_compiler_defaults_missing_criticality_to_mandatory() -> None:
    compiler = MandateCompiler()
    count, mandates = compiler.parse_mandate_spec(
        'mandate M001 {\n  title: "Bootstrap"\n}\n'
    )

    assert count == 1
    assert mandates[0]["criticality"] == "MANDATORY"


def test_generate_metadata_returns_false_when_dump_fails(
    tmp_path: Path, monkeypatch
) -> None:
    compiler = _make_compiler(tmp_path)

    def _boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(
        "providence_wizard.orchestration.phase5_artifact_compiler.json.dump",
        _boom,
    )

    assert compiler.generate_metadata() is False


def test_generate_metadata_sets_fingerprint_and_timestamp(tmp_path: Path) -> None:
    compiler = _make_compiler(tmp_path)

    assert compiler.generate_metadata() is True

    payload = json.loads(
        (tmp_path / ".providence" / "metadata.json").read_text(encoding="utf-8")
    )
    assert compiler.governance_fingerprint == payload["fingerprints"]["combined"]
    assert compiler.generated_at == payload["generated_at"]
