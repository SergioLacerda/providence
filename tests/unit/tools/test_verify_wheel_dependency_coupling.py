"""Tests for tools.release.verify_wheel_dependency_coupling."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tools.release.verify_wheel_dependency_coupling import (
    verify_wheel_dependency_coupling,
)


def _write_wheel(dist: Path, name: str, version: str, requires: list[str]) -> None:
    dist.mkdir(parents=True, exist_ok=True)
    wheel = dist / f"{name}-{version}-py3-none-any.whl"
    metadata_lines = [
        "Metadata-Version: 2.1",
        f"Name: {name.replace('_', '-')}",
        f"Version: {version}",
    ] + [f"Requires-Dist: {req}" for req in requires]
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"{name}-{version}.dist-info/METADATA", "\n".join(metadata_lines) + "\n"
        )


def test_passes_when_all_internal_deps_version_coupled(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _write_wheel(dist, "providence_core", "1.0.3", ["msgpack>=1.2.1"])
    _write_wheel(
        dist, "providence_cli", "1.0.3", ["providence-core>=1.0", "typer>=0.9.0"]
    )

    verify_wheel_dependency_coupling(dist)


def test_fails_when_internal_dep_wheel_missing(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _write_wheel(dist, "providence_cli", "1.0.3", ["providence-core>=1.0"])

    with pytest.raises(SystemExit, match="no wheel in dist/"):
        verify_wheel_dependency_coupling(dist)


def test_fails_when_internal_dep_version_differs(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _write_wheel(dist, "providence_core", "1.0.2", [])
    _write_wheel(dist, "providence_cli", "1.0.3", ["providence-core>=1.0"])

    with pytest.raises(SystemExit, match="same-release coupling"):
        verify_wheel_dependency_coupling(dist)


def test_ignores_external_dependencies(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _write_wheel(
        dist, "providence_core", "1.0.3", ["msgpack>=1.2.1", "structlog>=23.0"]
    )

    verify_wheel_dependency_coupling(dist)


def test_fails_when_dist_has_no_wheels(tmp_path: Path) -> None:
    (tmp_path / "dist").mkdir()

    with pytest.raises(SystemExit, match="no providence_\\* wheels"):
        verify_wheel_dependency_coupling(tmp_path / "dist")
