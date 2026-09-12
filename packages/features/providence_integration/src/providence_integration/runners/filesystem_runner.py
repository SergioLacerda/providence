"""Filesystem Runner."""

import shutil
from pathlib import Path

from providence_integration.engine.types import (
    FilesystemCopyInputs,
    FilesystemCreateStructureInputs,
    RuntimeContext,
)


def _is_safe_path(base: Path, target: Path) -> bool:
    """Verify that target path is within base directory (prevent path traversal)"""
    try:
        resolved_base = base.resolve()
        resolved_target = target.resolve()
        return (
            resolved_base in resolved_target.parents or resolved_base == resolved_target
        )
    except (OSError, ValueError):
        return False


def run_filesystem_create_structure(
    inputs: FilesystemCreateStructureInputs, context: RuntimeContext, spec_dir: Path
) -> None:
    """Run Filesystem Create Structure."""
    del spec_dir
    working_dir = context.get("working_dir", Path.cwd())
    for directory in inputs.directories:
        target_path = (working_dir / directory).resolve()
        if not _is_safe_path(working_dir, target_path):
            raise PermissionError(
                f"Security violation: path traversal detected for {directory}"
            )
        target_path.mkdir(parents=True, exist_ok=True)


def run_filesystem_copy(
    inputs: FilesystemCopyInputs, context: RuntimeContext, spec_dir: Path
) -> None:
    """Run Filesystem Copy."""
    working_dir = context.get("working_dir", Path.cwd())
    src = (spec_dir / inputs.from_).resolve()
    dst = (working_dir / inputs.to).resolve()

    if not _is_safe_path(working_dir, dst):
        raise PermissionError(
            f"Security violation: path traversal detected for {inputs.to}"
        )

    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    elif src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
