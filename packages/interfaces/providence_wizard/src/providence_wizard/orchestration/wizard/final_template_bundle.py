"""Final-template consolidation and layout helpers."""

import shutil
from pathlib import Path
from typing import TypedDict

from ._final_template_layout import (
    merge_and_normalize_source,
    move_audit_artifacts,
    move_compiled_artifacts,
    move_manifest,
    organize_final_template_layout,
    remove_deployment_only_dirs,
)
from ._final_template_layout_helpers import ensure_context_cache

__all__ = [
    "ConsolidationResult",
    "consolidate_final_template",
    "ensure_context_cache",
    "merge_and_normalize_source",
    "move_audit_artifacts",
    "move_compiled_artifacts",
    "move_manifest",
    "organize_final_template_layout",
    "remove_deployment_only_dirs",
    "validate_awareness_pack",
]


class ConsolidationResult(TypedDict):
    """ConsolidationResult."""

    success: bool
    source_dir: str
    target_dir: str
    moved_items: int
    error: str
    awareness_pack: dict[str, object]


def validate_awareness_pack(target_dir: Path) -> dict[str, object]:
    """Validate skills/commands/CLI awareness artifacts in consolidated output."""
    required_paths = [
        ".providence/seedlings/ACTIVATION_GUIDE.md",
        "AGENTS.md",
        ".github/prompts",
        ".cursor/rules/sdd-commands.mdc",
        ".gemini/commands.md",
        "CLAUDE.md",
    ]
    missing = [item for item in required_paths if not (target_dir / item).exists()]
    return {
        "status": "ok" if not missing else "incomplete",
        "missing_items": missing,
    }


def consolidate_final_template(
    *,
    source_dir: Path,
    target_dir: Path,
    compiled_files: tuple[str, ...],
    audit_files: tuple[str, ...],
    manifest_file: str,
    context_cache_relative_file: str,
) -> ConsolidationResult:
    """Move compiled artifacts into final-template and normalize layout."""
    if not source_dir.exists():
        return {
            "success": False,
            "source_dir": str(source_dir),
            "target_dir": str(target_dir),
            "moved_items": 0,
            "error": f"Compiled artifacts directory not found: {source_dir}",
            "awareness_pack": {"status": "incomplete", "missing_items": []},
        }

    source_items = [item for item in source_dir.iterdir()]
    if not source_items:
        return {
            "success": False,
            "source_dir": str(source_dir),
            "target_dir": str(target_dir),
            "moved_items": 0,
            "error": f"No artifacts found in {source_dir} to consolidate",
            "awareness_pack": {"status": "incomplete", "missing_items": []},
        }

    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    for item in source_items:
        shutil.move(str(item), str(target_dir / item.name))

    organize_final_template_layout(
        target_dir=target_dir,
        compiled_files=compiled_files,
        audit_files=audit_files,
        manifest_file=manifest_file,
        context_cache_relative_file=context_cache_relative_file,
    )

    source_dir.mkdir(parents=True, exist_ok=True)
    awareness_pack = validate_awareness_pack(target_dir)
    return {
        "success": True,
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "moved_items": len(source_items),
        "error": "",
        "awareness_pack": awareness_pack,
    }
