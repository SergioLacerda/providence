"""Providence runtime authority path helpers.

This module owns the `.providence` runtime paths.  The older
`sdd_authority` module remains as a compatibility import surface.
"""

from providence_cli.utils.sdd_authority import (
    PathPolicyViolation,
    compiled_active_dir,
    enforce_path_policy,
    profile_active_path,
    resolve_workspace_root,
    source_semantic_dir,
)

__all__ = [
    "PathPolicyViolation",
    "compiled_active_dir",
    "enforce_path_policy",
    "profile_active_path",
    "resolve_workspace_root",
    "source_semantic_dir",
]
