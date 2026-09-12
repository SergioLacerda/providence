"""Workspace and profile resolution helpers."""

from __future__ import annotations

import configparser
import os
import uuid
from pathlib import Path
from typing import cast

from ._environment_models import (
    ProfileContext,
    SddProfile,
    WorkspaceNotInitializedError,
)


def _workspace_root_from_env() -> Path | None:
    raw = os.environ.get("SDD_WORKSPACE_ROOT", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def find_workspace_root(start: Path | None = None) -> Path | None:
    """Walk up from `start` looking for a `.providence/` directory."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".providence").is_dir():
            return candidate
    return None


def resolve_venv_python(venv_dir: Path) -> Path:
    linux_python = venv_dir / "bin" / "python"
    if linux_python.exists():
        return linux_python

    windows_python = venv_dir / "Scripts" / "python.exe"
    if windows_python.exists():
        return windows_python

    raise RuntimeError("Could not find virtualenv python executable")


def resolve_venv_sdd(venv_dir: Path) -> Path:
    linux_providence = venv_dir / "bin" / "providence"
    if linux_providence.exists():
        return linux_providence

    windows_providence = venv_dir / "Scripts" / "providence.exe"
    if windows_providence.exists():
        return windows_providence

    raise RuntimeError("Could not find providence executable in virtualenv")


def resolve_sdd_child_cmd() -> str:
    """Resolve a deterministic Providence executable for child subprocess steps.

    Resolution order:
    1. sys.argv[0] when it is an absolute path to a providence console script.
    2. providence / providence.exe beside the current Python executable.
    3. Bare "providence" as a PATH-dependent fallback.
    """
    import sys

    argv0 = Path(sys.argv[0])
    if (
        argv0.name in ("providence", "providence.exe")
        and argv0.is_absolute()
        and argv0.exists()
    ):
        return str(argv0)

    python_bin_dir = Path(sys.executable).parent
    for candidate_name in ("providence", "providence.exe"):
        candidate = python_bin_dir / candidate_name
        if candidate.exists():
            return str(candidate)

    return "providence"


def resolve_profile(
    root: Path | None = None,
    override: str | None = None,
) -> ProfileContext:
    """Resolve the active workspace profile with no silent fallback."""
    effective_override = (
        override or os.environ.get("SDD_PROFILE", "").strip().lower() or None
    )
    if effective_override in ("master", "client"):
        workspace_root = root or find_workspace_root() or Path.cwd()
        return ProfileContext(
            type=cast(SddProfile, effective_override),
            name=effective_override,
            workspace_id="",
            core_hash="",
            root=workspace_root,
        )

    workspace_root = root or find_workspace_root() or Path.cwd()
    if (root is None) and (find_workspace_root() is None):
        raise WorkspaceNotInitializedError(Path.cwd())

    profile_path = workspace_root / ".providence" / "profile"
    if not profile_path.exists():
        raise WorkspaceNotInitializedError(workspace_root)

    parser = configparser.ConfigParser()
    parser.read(profile_path)
    raw_type = parser.get("sdd", "type", fallback="").strip().lower()
    if raw_type not in ("master", "client"):
        raise WorkspaceNotInitializedError(workspace_root)

    return ProfileContext(
        type=cast(SddProfile, raw_type),
        name=parser.get("sdd", "name", fallback=raw_type),
        workspace_id=parser.get("sdd", "workspace_id", fallback=""),
        core_hash=parser.get("sdd", "core_hash", fallback=""),
        root=workspace_root,
        language=parser.get("sdd", "language", fallback=None) or None,
    )


def detect_profile(root: Path | None = None) -> SddProfile:
    try:
        return resolve_profile(root=root).type
    except WorkspaceNotInitializedError:
        return "client"


def write_profile(
    root: Path,
    profile_type: SddProfile,
    name: str,
    language: str | None = None,
) -> ProfileContext:
    sdd_dir = root / ".providence"
    sdd_dir.mkdir(parents=True, exist_ok=True)
    workspace_id = str(uuid.uuid4())
    profile_path = sdd_dir / "profile"

    section = {
        "version": "1",
        "workspace_id": workspace_id,
        "type": profile_type,
        "name": name,
        "core_hash": "",
    }
    if language:
        section["language"] = language

    parser = configparser.ConfigParser()
    parser["sdd"] = section
    with open(profile_path, "w", encoding="utf-8") as handle:
        parser.write(handle)

    return ProfileContext(
        type=profile_type,
        name=name,
        workspace_id=workspace_id,
        core_hash="",
        root=root,
        language=language,
    )
