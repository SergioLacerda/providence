"""Layout normalization for the final-template directory."""

from __future__ import annotations

import shutil
from pathlib import Path

from providence_wizard.constants import RUNTIME_DIRNAME

from ._final_template_layout_helpers import ensure_context_cache


def organize_final_template_layout(
    *,
    target_dir: Path,
    compiled_files: tuple[str, ...],
    audit_files: tuple[str, ...],
    manifest_file: str,
    context_cache_relative_file: str,
) -> None:
    """Keep runtime governance artifacts under the runtime directory."""
    sdd_dir = target_dir / RUNTIME_DIRNAME
    move_compiled_artifacts(target_dir, sdd_dir, compiled_files)
    move_audit_artifacts(target_dir, sdd_dir, audit_files)
    move_manifest(target_dir, sdd_dir, manifest_file)
    merge_and_normalize_source(target_dir, sdd_dir)
    remove_deployment_only_dirs(target_dir)
    ensure_context_cache(target_dir, context_cache_relative_file)


def move_compiled_artifacts(
    target_dir: Path, sdd_dir: Path, compiled_files: tuple[str, ...]
) -> None:
    """Move governance compiled artifacts to .providence/compiled."""
    sdd_compiled_dir = sdd_dir / "compiled"
    sdd_audit_dir = sdd_compiled_dir / "audit"
    sdd_compiled_dir.mkdir(parents=True, exist_ok=True)
    sdd_audit_dir.mkdir(parents=True, exist_ok=True)

    for filename in compiled_files:
        top_level_file = target_dir / filename
        nested_file = sdd_compiled_dir / filename
        if not top_level_file.exists():
            continue
        if nested_file.exists():
            nested_file.unlink()
        shutil.move(str(top_level_file), str(nested_file))


def move_audit_artifacts(
    target_dir: Path, sdd_dir: Path, audit_files: tuple[str, ...]
) -> None:
    """Move JSON governance snapshots and audit dir to .providence/audit."""
    sdd_audit_dir = sdd_dir / "audit"
    sdd_compiled_audit_dir = sdd_dir / "compiled" / "audit"
    sdd_audit_dir.mkdir(parents=True, exist_ok=True)
    sdd_compiled_audit_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("governance-core.json", "governance-client.json"):
        top_level_file = target_dir / filename
        nested_file = sdd_audit_dir / filename
        if not top_level_file.exists():
            continue
        if nested_file.exists():
            nested_file.unlink()
        shutil.move(str(top_level_file), str(nested_file))

    top_level_audit_dir = target_dir / "audit"
    if top_level_audit_dir.exists() and top_level_audit_dir.is_dir():
        shutil.copytree(top_level_audit_dir, sdd_audit_dir, dirs_exist_ok=True)
        shutil.rmtree(top_level_audit_dir)

    for filename in audit_files:
        top_level_file = target_dir / filename
        nested_file = sdd_audit_dir / filename
        if not top_level_file.exists():
            continue
        if nested_file.exists():
            nested_file.unlink()
        shutil.move(str(top_level_file), str(nested_file))

    shutil.copytree(sdd_audit_dir, sdd_compiled_audit_dir, dirs_exist_ok=True)


def move_manifest(target_dir: Path, sdd_dir: Path, manifest_file: str) -> None:
    """Move deployment manifest to .providence and mirror it in .providence/compiled/audit."""
    top_level_manifest = target_dir / manifest_file
    sdd_manifest = sdd_dir / manifest_file
    audit_manifest = sdd_dir / "compiled" / "audit" / manifest_file
    if not top_level_manifest.exists():
        return
    sdd_manifest.parent.mkdir(parents=True, exist_ok=True)
    audit_manifest.parent.mkdir(parents=True, exist_ok=True)

    if sdd_manifest.exists():
        sdd_manifest.unlink()
    if audit_manifest.exists():
        audit_manifest.unlink()

    shutil.move(str(top_level_manifest), str(sdd_manifest))
    shutil.copy2(str(sdd_manifest), str(audit_manifest))


def merge_and_normalize_source(target_dir: Path, sdd_dir: Path) -> None:
    """Merge governance source files under .providence/source."""
    top_level_source = target_dir / "source"
    nested_source = sdd_dir / "source"

    if not (top_level_source.exists() and top_level_source.is_dir()):
        return

    nested_source.mkdir(parents=True, exist_ok=True)
    for item in top_level_source.iterdir():
        destination = nested_source / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
            shutil.rmtree(item)
            continue
        if destination.exists():
            destination.unlink()
        shutil.move(str(item), str(destination))

    if not any(top_level_source.iterdir()):
        top_level_source.rmdir()


def remove_deployment_only_dirs(target_dir: Path) -> None:
    """Remove directories used only in deployment, not in final handoff."""
    backup_dir = target_dir / "backup"
    if backup_dir.exists() and backup_dir.is_dir():
        shutil.rmtree(backup_dir)
