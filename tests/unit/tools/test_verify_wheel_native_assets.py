"""Tests for tools.release.verify_wheel_native_assets."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tools.release.validate_release_assets import REQUIRED_COMPILER_ASSETS
from tools.release.verify_wheel_native_assets import (
    WHEEL_NATIVE_PREFIX,
    verify_wheel_native_assets,
)


def _write_wheel(
    dist: Path,
    *,
    assets: tuple[str, ...] = REQUIRED_COMPILER_ASSETS,
    empty: frozenset[str] = frozenset(),
    name: str = "providence_core-1.0.3-py3-none-any.whl",
) -> Path:
    dist.mkdir(parents=True, exist_ok=True)
    wheel = dist / name
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("providence_core/__init__.py", "")
        for asset in assets:
            payload = b"" if asset in empty else b"binary-bytes"
            archive.writestr(WHEEL_NATIVE_PREFIX + asset, payload)
    return wheel


def test_passes_when_all_assets_bundled(tmp_path: Path) -> None:
    wheel = _write_wheel(tmp_path / "dist")

    assert verify_wheel_native_assets(tmp_path / "dist") == wheel


def test_fails_when_asset_missing(tmp_path: Path) -> None:
    _write_wheel(tmp_path / "dist", assets=REQUIRED_COMPILER_ASSETS[:-1])

    with pytest.raises(SystemExit, match="missing bundled compiler binaries"):
        verify_wheel_native_assets(tmp_path / "dist")


def test_fails_when_asset_empty(tmp_path: Path) -> None:
    _write_wheel(tmp_path / "dist", empty=frozenset({"sdd-compile-windows-amd64.exe"}))

    with pytest.raises(SystemExit, match="empty compiler binaries"):
        verify_wheel_native_assets(tmp_path / "dist")


def test_fails_when_no_wheel_found(tmp_path: Path) -> None:
    (tmp_path / "dist").mkdir()

    with pytest.raises(SystemExit, match="no providence_core wheel"):
        verify_wheel_native_assets(tmp_path / "dist")
