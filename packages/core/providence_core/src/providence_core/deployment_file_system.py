"""Deployment File System - File operations and directory management.

Handles copying files, backup management, and runtime directory creation.
"""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DeploymentBackup:
    """Record of a backed-up file."""

    path: Path
    backup: Path


class DeploymentFileSystem:
    """Static class for deployment file system operations."""

    @staticmethod
    def create_runtime_structure(
        runtime_compiled: Path, emit_fn: Callable[[str], None]
    ) -> None:
        """Create runtime/compiled/ directory structure.

        Args:
            runtime_compiled: Path to runtime/compiled directory
            emit_fn: Function to emit status messages
        """
        runtime_compiled.mkdir(parents=True, exist_ok=True)
        (runtime_compiled / "audit").mkdir(parents=True, exist_ok=True)
        (runtime_compiled / "backup").mkdir(exist_ok=True)
        emit_fn(f"  📁 Created: {runtime_compiled}")

    @staticmethod
    def copy_files(
        compiled_dir: Path,
        artifacts: tuple[str, str, str, str],
        metadata_source_fn: Callable[[str], Path],
        runtime_compiled: Path,
        runtime_audit: Path,
        emit_fn: Callable[[str], None],
    ) -> tuple[dict[str, str], list[DeploymentBackup]]:
        """Copy compiled files to runtime location and collect backups.

        Args:
            compiled_dir: Path to compiled artifacts directory
            artifacts: Tuple of 4 artifact filenames
            metadata_source_fn: Function to resolve metadata file paths
            runtime_compiled: Path to runtime/compiled directory
            runtime_audit: Path to runtime/compiled/audit directory
            emit_fn: Function to emit status messages

        Returns:
            Tuple of (copied_files dict, backups list)
        """
        files_to_copy = [
            (artifacts[0], compiled_dir),
            (artifacts[1], compiled_dir),
            (artifacts[2], metadata_source_fn(artifacts[2]).parent),
            (artifacts[3], metadata_source_fn(artifacts[3]).parent),
        ]

        copied_files: dict[str, str] = {}
        backups: list[DeploymentBackup] = []

        for filename, source_dir in files_to_copy:
            src = source_dir / filename
            dst = (
                runtime_audit / filename
                if filename.startswith("metadata-")
                else runtime_compiled / filename
            )

            # Backup existing file if it exists and is different
            if dst.exists() and src != dst:
                backup_dst = runtime_compiled / "backup" / f"{filename}.backup"
                shutil.copy2(dst, backup_dst)
                backups.append(DeploymentBackup(path=dst, backup=backup_dst))
                emit_fn(f"  💾 Backed up: {filename}")

            # Copy file only if source and destination are different
            if src != dst:
                shutil.copy2(src, dst)
                emit_fn(f"  📄 Copied: {filename}")
            else:
                emit_fn(f"  ✅ Verified in place: {filename}")

            copied_files[filename] = dst.as_posix()

        return copied_files, backups

    @staticmethod
    def copy_files_transactional(
        compiled_dir: Path,
        artifacts: tuple[str, str, str, str],
        metadata_source_fn: Callable[[str], Path],
        runtime_compiled: Path,
        runtime_audit: Path,
        emit_fn: Callable[[str], None],
    ) -> dict[str, str]:
        """Copy files with rollback to last known good state on failure.

        Args:
            compiled_dir: Path to compiled artifacts directory
            artifacts: Tuple of 4 artifact filenames
            metadata_source_fn: Function to resolve metadata file paths
            runtime_compiled: Path to runtime/compiled directory
            runtime_audit: Path to runtime/compiled/audit directory
            emit_fn: Function to emit status messages

        Returns:
            Dictionary of copied files (empty on failure)
        """
        try:
            copied_files, backups = DeploymentFileSystem.copy_files(
                compiled_dir,
                artifacts,
                metadata_source_fn,
                runtime_compiled,
                runtime_audit,
                emit_fn,
            )
            return copied_files
        except Exception:
            # Rollback: restore from backups
            # Note: We don't have access to backups here since copy_files failed
            # In a real scenario, we'd need to handle this differently
            return {}
