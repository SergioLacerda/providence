"""Tests for GovernanceLoader._resolve_metadata_path."""

from __future__ import annotations

from pathlib import Path

from providence_core.utils.loader import GovernanceLoader


def _make_loader(compiled_dir: Path) -> GovernanceLoader:
    loader = object.__new__(GovernanceLoader)
    loader.compiled_dir = compiled_dir
    return loader


def test_resolve_metadata_path_returns_audit_path(tmp_path: Path) -> None:
    """Always returns compiled/audit/<filename> — canonical path."""
    compiled = tmp_path / "compiled"
    compiled.mkdir()
    (compiled / "audit").mkdir()
    (compiled / "audit" / "metadata.json").write_text("{}", encoding="utf-8")

    loader = _make_loader(compiled)
    result = loader._resolve_metadata_path("metadata.json")

    assert result == compiled / "audit" / "metadata.json"


def test_resolve_metadata_path_returns_audit_path_even_when_absent(
    tmp_path: Path,
) -> None:
    """Returns audit/<filename> even when only root/<filename> exists.

    Legacy fallback removed — caller is responsible for handling missing file.
    """
    compiled = tmp_path / "compiled"
    compiled.mkdir()
    (compiled / "metadata.json").write_text("{}", encoding="utf-8")

    loader = _make_loader(compiled)
    result = loader._resolve_metadata_path("metadata.json")

    assert result == compiled / "audit" / "metadata.json"
    assert not result.exists()  # file is in root, not in audit/ — caller handles this
