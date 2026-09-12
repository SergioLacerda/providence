from __future__ import annotations

from pathlib import Path

import pytest

from tools.release.validate_release_assets import (
    REQUIRED_ASSETS,
    REQUIRED_CLI_ASSETS,
    REQUIRED_COMPILER_ASSETS,
    ReleaseAssetValidationError,
    validate_release_assets,
)

_DIGEST = "0" * 64
_ALL_REQUIRED_BINARIES = REQUIRED_COMPILER_ASSETS + REQUIRED_CLI_ASSETS


def _write_valid_dist(root: Path) -> Path:
    dist = root / "dist"
    dist.mkdir()
    for asset in _ALL_REQUIRED_BINARIES:
        (dist / asset).write_bytes(b"binary-payload")
    sums = "\n".join(f"{_DIGEST}  {asset}" for asset in _ALL_REQUIRED_BINARIES)
    (dist / "SHA256SUMS").write_text(sums + "\n", encoding="utf-8")
    return dist


def test_valid_dist_passes(tmp_path: Path) -> None:
    dist = _write_valid_dist(tmp_path)
    validate_release_assets(dist)  # must not raise


def test_missing_asset_fails(tmp_path: Path) -> None:
    dist = _write_valid_dist(tmp_path)
    (dist / "sdd-compile-linux-amd64").unlink()

    with pytest.raises(ReleaseAssetValidationError, match="sdd-compile-linux-amd64"):
        validate_release_assets(dist)


def test_empty_asset_fails(tmp_path: Path) -> None:
    dist = _write_valid_dist(tmp_path)
    (dist / "sdd-compile-linux-amd64").write_bytes(b"")

    with pytest.raises(ReleaseAssetValidationError, match="missing or empty"):
        validate_release_assets(dist)


def test_missing_sha256sums_fails(tmp_path: Path) -> None:
    dist = _write_valid_dist(tmp_path)
    (dist / "SHA256SUMS").unlink()

    with pytest.raises(ReleaseAssetValidationError, match="SHA256SUMS"):
        validate_release_assets(dist)


def test_sha256sums_missing_entry_fails(tmp_path: Path) -> None:
    dist = _write_valid_dist(tmp_path)
    remaining = [a for a in _ALL_REQUIRED_BINARIES if a != "sdd-compile-darwin-arm64"]
    sums = "\n".join(f"{_DIGEST}  {asset}" for asset in remaining)
    (dist / "SHA256SUMS").write_text(sums + "\n", encoding="utf-8")

    with pytest.raises(ReleaseAssetValidationError, match="sdd-compile-darwin-arm64"):
        validate_release_assets(dist)


def test_sha256sums_missing_cli_entry_fails(tmp_path: Path) -> None:
    dist = _write_valid_dist(tmp_path)
    remaining = [a for a in _ALL_REQUIRED_BINARIES if a != "providence-darwin-arm64"]
    sums = "\n".join(f"{_DIGEST}  {asset}" for asset in remaining)
    (dist / "SHA256SUMS").write_text(sums + "\n", encoding="utf-8")

    with pytest.raises(ReleaseAssetValidationError, match="providence-darwin-arm64"):
        validate_release_assets(dist)


def test_sha256sums_entry_with_dist_prefix_fails(tmp_path: Path) -> None:
    dist = _write_valid_dist(tmp_path)
    sums = "\n".join(f"{_DIGEST}  dist/{asset}" for asset in _ALL_REQUIRED_BINARIES)
    (dist / "SHA256SUMS").write_text(sums + "\n", encoding="utf-8")

    with pytest.raises(ReleaseAssetValidationError, match="bare filename"):
        validate_release_assets(dist)


def test_required_assets_includes_sums_file() -> None:
    assert REQUIRED_ASSETS[-1] == "SHA256SUMS"
    assert (
        len(REQUIRED_ASSETS)
        == len(REQUIRED_COMPILER_ASSETS) + len(REQUIRED_CLI_ASSETS) + 1
    )


def test_required_cli_assets_has_no_darwin_amd64() -> None:
    # PyInstaller can't cross-compile; macos-latest runners are arm64-only —
    # see the comment in validate_release_assets.py.
    assert "providence-darwin-amd64" not in REQUIRED_CLI_ASSETS
    assert "providence-darwin-arm64" in REQUIRED_CLI_ASSETS
