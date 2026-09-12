"""Tests for the opt-in direct-to-root deployment (Workstream 3)."""

from __future__ import annotations

import json
from pathlib import Path

from providence_wizard.orchestration.wizard._direct_root_deploy import deploy_to_root


def _make_final_template(tmp_path: Path, fingerprint: str = "abc123") -> Path:
    source = tmp_path / "final-template"
    (source / ".providence").mkdir(parents=True)
    (source / ".providence" / "metadata.json").write_text(
        json.dumps({"governance_fingerprint": fingerprint}), encoding="utf-8"
    )
    (source / "AGENTS.md").write_text("root seed content\n", encoding="utf-8")
    return source


def test_new_files_are_created(tmp_path: Path) -> None:
    source = _make_final_template(tmp_path)
    target = tmp_path / "project"
    target.mkdir()

    result = deploy_to_root(target_root=target, final_template_dir=source)

    assert sorted(result.created) == [".providence/metadata.json", "AGENTS.md"]
    assert result.updated == []
    assert result.unchanged == []
    assert result.skipped == []
    assert (target / "AGENTS.md").read_text(encoding="utf-8") == "root seed content\n"


def test_rerun_with_identical_content_is_unchanged(tmp_path: Path) -> None:
    source = _make_final_template(tmp_path)
    target = tmp_path / "project"
    target.mkdir()
    deploy_to_root(target_root=target, final_template_dir=source)

    result = deploy_to_root(target_root=target, final_template_dir=source)

    assert result.created == []
    assert result.updated == []
    assert sorted(result.unchanged) == [".providence/metadata.json", "AGENTS.md"]


def test_managed_file_is_updated_when_source_changes(tmp_path: Path) -> None:
    source = _make_final_template(tmp_path)
    target = tmp_path / "project"
    target.mkdir()
    deploy_to_root(target_root=target, final_template_dir=source)

    (source / "AGENTS.md").write_text("updated seed content\n", encoding="utf-8")
    result = deploy_to_root(target_root=target, final_template_dir=source)

    assert "AGENTS.md" in result.updated
    assert (target / "AGENTS.md").read_text(
        encoding="utf-8"
    ) == "updated seed content\n"


def test_unmanaged_file_is_never_overwritten(tmp_path: Path) -> None:
    """A pre-existing, unmanaged file at the target must be left alone (skipped)."""
    source = _make_final_template(tmp_path)
    target = tmp_path / "project"
    target.mkdir()
    (target / "AGENTS.md").write_text("user's own AGENTS.md\n", encoding="utf-8")

    result = deploy_to_root(target_root=target, final_template_dir=source)

    assert "AGENTS.md" in result.skipped
    assert (target / "AGENTS.md").read_text(
        encoding="utf-8"
    ) == "user's own AGENTS.md\n"


def test_file_removed_from_source_is_reported_but_not_deleted(tmp_path: Path) -> None:
    source = _make_final_template(tmp_path)
    target = tmp_path / "project"
    target.mkdir()
    deploy_to_root(target_root=target, final_template_dir=source)

    (source / "AGENTS.md").unlink()
    result = deploy_to_root(target_root=target, final_template_dir=source)

    assert "AGENTS.md" in result.removed
    assert (target / "AGENTS.md").exists()  # never deleted from disk


def test_manifest_records_generator_and_fingerprint(tmp_path: Path) -> None:
    source = _make_final_template(tmp_path, fingerprint="deadbeef99")
    target = tmp_path / "project"
    target.mkdir()

    deploy_to_root(target_root=target, final_template_dir=source)

    manifest = json.loads(
        (target / ".providence" / "runtime" / "direct-root-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["generator"] == "providence_wizard.direct_root_deploy"
    assert manifest["snapshot_fingerprint"] == "deadbeef99"
    assert "AGENTS.md" in manifest["managed_files"]
