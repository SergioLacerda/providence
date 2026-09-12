"""Shared helpers for governance loading."""

from __future__ import annotations

from pathlib import Path


def resolve_metadata_path(filename: str, base_dir: Path) -> Path:
    return base_dir / "audit" / filename


def resolve_existing_metadata_path(filename: str, base_dir: Path) -> Path:
    canonical = resolve_metadata_path(filename, base_dir)
    if canonical.exists():
        return canonical
    return base_dir / filename
