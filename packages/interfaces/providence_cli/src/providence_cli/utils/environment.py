"""Environment and path utilities for cross-platform CLI execution.
Delegates to providence_core for framework-wide consistency.
"""

from providence_core.utils.environment import (
    detect_repo_root,
    get_sdd_paths,
    resolve_venv_python,
    resolve_venv_sdd,
)

__all__ = [
    "detect_repo_root",
    "resolve_venv_python",
    "resolve_venv_sdd",
    "get_sdd_paths",
]
