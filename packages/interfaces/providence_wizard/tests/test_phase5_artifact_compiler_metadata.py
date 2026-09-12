from __future__ import annotations

import json
from pathlib import Path

from providence_wizard.orchestration.phase5_artifact_compiler import ArtifactCompiler


def test_generate_metadata_includes_language_policy(tmp_path: Path) -> None:
    sdd_dir = tmp_path / ".providence"
    runtime_dir = sdd_dir / "runtime"
    sdd_dir.mkdir()
    runtime_dir.mkdir(parents=True)

    compiler = ArtifactCompiler(
        repo_root=tmp_path,
        sdd_dir=sdd_dir,
        runtime_dir=runtime_dir,
        mandates=[{"id": "M011", "title": "English Language Standard"}],
        guidelines={"G021": {"id": "G021"}, "G022": {"id": "G022"}},
        guidelines_by_category={"communication": [{"id": "G021"}]},
        config={
            "language": "Python",
            "language_context": {"preferred_human_language": "English"},
        },
        verbose=False,
        emitter=lambda _msg: None,
    )

    assert compiler.generate_metadata() is True

    metadata = json.loads((sdd_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["guidelines_count"] == 2
    assert metadata["language_policy"]["mandate_anchor"] == "M011"
    assert "workspace_local_docs" in metadata["language_policy"]["contextual_surfaces"]
    assert "analysis_docs" in metadata["language_policy"]["contextual_surfaces"]
    assert metadata["language_policy"]["workspace_local_docs_paths"] == [".analysis/"]


def test_generate_metadata_top_level_fingerprint_mirrors_combined(
    tmp_path: Path,
) -> None:
    """governance_fingerprint (top-level) must always equal fingerprints.combined.

    Both values are derived from the same compiler-computed hash, so they can
    never diverge  closing the drift bug where .providence/agent-instructions.md
    referenced a top-level field that did not exist.
    """
    sdd_dir = tmp_path / ".providence"
    runtime_dir = sdd_dir / "runtime"
    sdd_dir.mkdir()
    runtime_dir.mkdir(parents=True)

    compiler = ArtifactCompiler(
        repo_root=tmp_path,
        sdd_dir=sdd_dir,
        runtime_dir=runtime_dir,
        mandates=[{"id": "M001", "title": "Clean Architecture"}],
        guidelines={},
        guidelines_by_category={},
        config={},
        verbose=False,
        emitter=lambda _msg: None,
    )

    assert compiler.generate_metadata() is True

    metadata = json.loads((sdd_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["governance_fingerprint"] == metadata["fingerprints"]["combined"]
    assert compiler.governance_fingerprint == metadata["governance_fingerprint"]
