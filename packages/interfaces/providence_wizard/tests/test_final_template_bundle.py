"""Tests for final_template_bundle consolidation helpers."""

from __future__ import annotations

from pathlib import Path

from providence_wizard.orchestration.wizard.final_template_bundle import (
    consolidate_final_template,
    ensure_context_cache,
    merge_and_normalize_source,
    move_audit_artifacts,
    move_compiled_artifacts,
    move_manifest,
    remove_deployment_only_dirs,
    validate_awareness_pack,
)

_COMPILED_FILES = ("governance-core.compiled.msgpack",)
_AUDIT_FILES = ("metadata-core.json",)
_MANIFEST = "DEPLOYMENT_MANIFEST.json"
_CONTEXT_CACHE = ".providence/context-cache.md"


def _make_source(tmp_path: Path) -> Path:
    source = tmp_path / "compiled-out"
    source.mkdir()
    (source / "governance-core.compiled.msgpack").write_bytes(b"\x00")
    (source / "metadata-core.json").write_text("{}", encoding="utf-8")
    return source


class TestConsolidateFinalTemplate:
    def test_success_moves_items(self, tmp_path: Path) -> None:
        source = _make_source(tmp_path)
        target = tmp_path / "final-template"
        result = consolidate_final_template(
            source_dir=source,
            target_dir=target,
            compiled_files=_COMPILED_FILES,
            audit_files=_AUDIT_FILES,
            manifest_file=_MANIFEST,
            context_cache_relative_file=_CONTEXT_CACHE,
        )
        assert result["success"] is True
        assert result["moved_items"] >= 1

    def test_missing_source_returns_failure(self, tmp_path: Path) -> None:
        result = consolidate_final_template(
            source_dir=tmp_path / "nonexistent",
            target_dir=tmp_path / "target",
            compiled_files=_COMPILED_FILES,
            audit_files=_AUDIT_FILES,
            manifest_file=_MANIFEST,
            context_cache_relative_file=_CONTEXT_CACHE,
        )
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_empty_source_returns_failure(self, tmp_path: Path) -> None:
        source = tmp_path / "empty"
        source.mkdir()
        result = consolidate_final_template(
            source_dir=source,
            target_dir=tmp_path / "target",
            compiled_files=_COMPILED_FILES,
            audit_files=_AUDIT_FILES,
            manifest_file=_MANIFEST,
            context_cache_relative_file=_CONTEXT_CACHE,
        )
        assert result["success"] is False
        assert "No artifacts" in result["error"]

    def test_existing_target_is_replaced(self, tmp_path: Path) -> None:
        source = _make_source(tmp_path)
        target = tmp_path / "final-template"
        target.mkdir()
        (target / "old-file.txt").write_text("old", encoding="utf-8")
        result = consolidate_final_template(
            source_dir=source,
            target_dir=target,
            compiled_files=_COMPILED_FILES,
            audit_files=_AUDIT_FILES,
            manifest_file=_MANIFEST,
            context_cache_relative_file=_CONTEXT_CACHE,
        )
        assert result["success"] is True
        assert not (target / "old-file.txt").exists()


class TestEnsureContextCache:
    def test_creates_cache_file(self, tmp_path: Path) -> None:
        ensure_context_cache(tmp_path, ".providence/context-cache.md")
        assert (tmp_path / ".providence" / "context-cache.md").exists()
        content = (tmp_path / ".providence" / "context-cache.md").read_text(
            encoding="utf-8"
        )
        assert "Current Objective" in content

    def test_does_not_overwrite_existing(self, tmp_path: Path) -> None:
        cache = tmp_path / ".providence" / "context-cache.md"
        cache.parent.mkdir(parents=True)
        cache.write_text("custom content", encoding="utf-8")
        ensure_context_cache(tmp_path, ".providence/context-cache.md")
        assert cache.read_text(encoding="utf-8") == "custom content"


class TestValidateAwarenessPack:
    def test_all_missing_returns_incomplete(self, tmp_path: Path) -> None:
        result = validate_awareness_pack(tmp_path)
        assert result["status"] == "incomplete"
        assert len(result["missing_items"]) > 0

    def test_all_present_returns_ok(self, tmp_path: Path) -> None:
        required = [
            ".providence/seedlings/ACTIVATION_GUIDE.md",
            "AGENTS.md",
            ".github/prompts",
            ".cursor/rules/sdd-commands.mdc",
            ".gemini/commands.md",
            "CLAUDE.md",
        ]
        for path in required:
            full = tmp_path / path
            full.parent.mkdir(parents=True, exist_ok=True)
            if full.suffix:
                full.write_text("x", encoding="utf-8")
            else:
                full.mkdir(exist_ok=True)
        result = validate_awareness_pack(tmp_path)
        assert result["status"] == "ok"


class TestMoveHelpers:
    def test_move_compiled_artifacts_skips_missing(self, tmp_path: Path) -> None:
        sdd = tmp_path / ".providence"
        move_compiled_artifacts(tmp_path, sdd, ("nonexistent.msgpack",))
        # Should not raise

    def test_move_manifest_skips_missing(self, tmp_path: Path) -> None:
        sdd = tmp_path / ".providence"
        move_manifest(tmp_path, sdd, "MISSING.json")
        # Should not raise

    def test_remove_deployment_only_dirs_removes_backup(self, tmp_path: Path) -> None:
        backup = tmp_path / "backup"
        backup.mkdir()
        (backup / "old.bin").write_bytes(b"\x00")
        remove_deployment_only_dirs(tmp_path)
        assert not backup.exists()

    def test_remove_deployment_only_dirs_noop_without_backup(
        self, tmp_path: Path
    ) -> None:
        remove_deployment_only_dirs(tmp_path)  # must not raise

    def test_merge_and_normalize_source_noop_when_no_source(
        self, tmp_path: Path
    ) -> None:
        merge_and_normalize_source(tmp_path, tmp_path / ".providence")  # must not raise

    def test_merge_and_normalize_source_merges_files(self, tmp_path: Path) -> None:
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "governance-core.json").write_text("{}", encoding="utf-8")
        sdd_dir = tmp_path / ".providence"
        merge_and_normalize_source(tmp_path, sdd_dir)
        assert (sdd_dir / "source" / "governance-core.json").exists()

    def test_move_audit_artifacts_with_audit_dir(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        (audit_dir / "metadata.json").write_text("{}", encoding="utf-8")
        sdd_dir = tmp_path / ".providence"
        move_audit_artifacts(tmp_path, sdd_dir, ())
        assert (sdd_dir / "audit" / "metadata.json").exists()

    def test_move_manifest_moves_and_copies(self, tmp_path: Path) -> None:
        manifest = tmp_path / "DEPLOYMENT_MANIFEST.json"
        manifest.write_text("{}", encoding="utf-8")
        sdd_dir = tmp_path / ".providence"
        move_manifest(tmp_path, sdd_dir, "DEPLOYMENT_MANIFEST.json")
        assert (sdd_dir / "DEPLOYMENT_MANIFEST.json").exists()
        assert (sdd_dir / "compiled" / "audit" / "DEPLOYMENT_MANIFEST.json").exists()

    def test_move_manifest_unlinks_existing_before_move(self, tmp_path: Path) -> None:
        manifest = tmp_path / "DEPLOYMENT_MANIFEST.json"
        manifest.write_text("new", encoding="utf-8")
        sdd_dir = tmp_path / ".providence"
        # Pre-create the target to exercise unlink path
        (sdd_dir).mkdir(parents=True)
        (sdd_dir / "DEPLOYMENT_MANIFEST.json").write_text("old", encoding="utf-8")
        audit = sdd_dir / "compiled" / "audit"
        audit.mkdir(parents=True)
        (audit / "DEPLOYMENT_MANIFEST.json").write_text("old", encoding="utf-8")
        move_manifest(tmp_path, sdd_dir, "DEPLOYMENT_MANIFEST.json")
        assert (sdd_dir / "DEPLOYMENT_MANIFEST.json").read_text(
            encoding="utf-8"
        ) == "new"

    def test_merge_source_with_subdirectory(self, tmp_path: Path) -> None:
        source_dir = tmp_path / "source" / "subdir"
        source_dir.mkdir(parents=True)
        (source_dir / "file.json").write_text("{}", encoding="utf-8")
        sdd_dir = tmp_path / ".providence"
        merge_and_normalize_source(tmp_path, sdd_dir)
        assert (sdd_dir / "source" / "subdir" / "file.json").exists()

    def test_merge_source_unlinks_existing_destination(self, tmp_path: Path) -> None:
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "existing.json").write_text("new", encoding="utf-8")
        sdd_dir = tmp_path / ".providence"
        # Pre-create destination to exercise unlink path
        (sdd_dir / "source").mkdir(parents=True)
        (sdd_dir / "source" / "existing.json").write_text("old", encoding="utf-8")
        merge_and_normalize_source(tmp_path, sdd_dir)
        assert (sdd_dir / "source" / "existing.json").read_text(
            encoding="utf-8"
        ) == "new"
