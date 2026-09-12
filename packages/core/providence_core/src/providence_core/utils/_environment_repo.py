"""Repository-level environment helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

__all__ = ["detect_repo_root", "get_project_config", "is_repo_root", "tomllib"]


def is_repo_root(path: Path) -> bool:
    """Check if a path is the SDD repository root."""
    required = [
        path / "pyproject.toml",
        path / "packages" / "core" / "providence_core" / "pyproject.toml",
    ]
    try:
        return all(p.exists() for p in required)
    except (PermissionError, OSError):
        return False


def detect_repo_root(*, allow_file_fallback: bool = True) -> Path:
    """Find the project root by searching from CWD and, optionally, `__file__`.

    The `__file__`-parents fallback answers "where does this installed
    package's code physically live," not "what project is the caller
    operating on." Under an editable/dev install of this monorepo, that is
    always this repository's own checkout — correct for this repo's own
    self-hosted dev tooling (`providence setup`, `providence test`, `providence lint`, ...), but
    wrong for any governance/client-content operation invoked against an
    unrelated project, where it silently leaks this repo's own content into
    that project instead of resolving (or raising, so the caller can fall
    back to `Path.cwd()`) the caller's actual working directory. Pass
    `allow_file_fallback=False` from any such call site.
    """
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if is_repo_root(candidate):
            return candidate

    if allow_file_fallback:
        try:
            file_path = Path(__file__).resolve()
        except NameError:
            file_path = None

        if file_path is not None:
            for candidate in file_path.parents:
                if is_repo_root(candidate):
                    return candidate

    if "GITHUB_WORKSPACE" in os.environ:
        return Path(os.environ["GITHUB_WORKSPACE"]).resolve()

    raise RuntimeError(
        "SDD Project root not found. Ensure you are running from within the repository."
    )


def get_project_config() -> dict[str, Any]:
    """Load configuration from the root `pyproject.toml`."""
    root = detect_repo_root()
    toml_path = root / "pyproject.toml"

    if not tomllib:
        return {}

    try:
        with open(toml_path, "rb") as handle:
            loaded = tomllib.load(handle)
            return cast(dict[str, Any], loaded)
    except Exception:
        return {}
