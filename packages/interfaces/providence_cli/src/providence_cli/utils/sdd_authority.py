"""Canonical `.providence` authority path helpers.

Centralizes the operational contract:
- active profile: `.providence/profile`
- executable governance: `.providence/compiled`
- semantic governance source: `.providence/source`
"""

from __future__ import annotations

import tempfile
from pathlib import Path

POLICY_ERR_CODE = "PATH_POLICY_VIOLATION"


class PathPolicyViolation(ValueError):
    """Raised when a path access violates artifact-first policy."""

    def __init__(self, requested_path: Path, reason: str, hint: str) -> None:
        self.code = POLICY_ERR_CODE
        self.requested_path = requested_path
        self.reason = reason
        self.hint = hint
        super().__init__(f"{self.code}: {reason} ({requested_path})")

    def as_dict(self) -> dict[str, str]:
        """As Dict."""
        return {
            "code": self.code,
            "requested_path": str(self.requested_path),
            "reason": self.reason,
            "hint": self.hint,
        }


def _repo_root() -> Path:
    """Resolve the "repo root" context for path-policy decisions.

    `allow_file_fallback=False`: under an editable/dev install of this
    monorepo, `detect_repo_root()`'s default fallback resolves to wherever
    the installed package's own code physically lives  this harness's own
    checkout  regardless of which project is actually being operated on.
    For `enforce_path_policy()` and `resolve_workspace_root()`, that leak
    is not just a content-correctness issue: `enforce_path_policy()`
    compares the caller's workspace against this "repo" to decide whether
    a client's own workspace counts as `is_repo_workspace`, so resolving to
    the harness's repo instead of the client's own directory makes that
    comparison fail and incorrectly rejects legitimate client operations.
    Falling back to `Path.cwd()` (the caller's actual working directory)
    when no real repo/workspace marker is found is the correct behavior for
    both a real standalone client and this harness's own dev loop (which
    already finds itself via the cwd-based search in the common case).
    """
    from providence_core.utils.environment import detect_repo_root, find_workspace_root

    ws_root = find_workspace_root()
    if ws_root is not None:
        return ws_root
    try:
        return detect_repo_root(allow_file_fallback=False)
    except RuntimeError:
        return Path.cwd().resolve()


def _workspace_root_from_env() -> Path | None:
    """Return SDD_WORKSPACE_ROOT if set (highest-priority explicit override).

    Delegates to providence_core's implementation  this used to be a
    character-for-character duplicate of
    `providence_core.utils.environment.workspace_root_from_env`, which risked the two
    silently diverging over time.
    """
    from providence_core.utils.environment import workspace_root_from_env

    return workspace_root_from_env()


def resolve_workspace_root(explicit_root: Path | None = None) -> Path:
    """Resolve workspace root for operational commands.

    Resolution order:
    1. ``explicit_root`` argument (``--workspace-root`` CLI flag)
    2. ``SDD_WORKSPACE_ROOT`` environment variable
    3. Detected workspace with ``.providence/profile``
    4. Repository root fallback
    """
    if explicit_root is not None:
        return explicit_root.expanduser().resolve()

    from_env = _workspace_root_from_env()
    if from_env is not None:
        return from_env

    from providence_core.utils.environment import find_workspace_root

    ws_root = find_workspace_root()
    if ws_root is not None:
        return ws_root.resolve()

    return _repo_root().resolve()


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _is_within_system_temp(path: Path) -> bool:
    """Return True when *path* is under the current system temp directory."""
    try:
        sys_tmp = Path(tempfile.gettempdir()).resolve()
    except Exception:  # nosec B110
        return False
    return _is_relative_to(path, sys_tmp)


def enforce_path_policy(
    requested_path: Path,
    *,
    workspace_root: Path,
    mode: str = "normal",
) -> Path:
    """Enforce artifact-first policy for normal mode and audit override mode."""
    req = requested_path.resolve()
    ws = workspace_root.resolve()
    repo = _repo_root().resolve()
    generated_root = (repo / "generated").resolve()

    if mode == "extraordinary_audit":
        # Explicit opt-in mode for bilateral framework/artifact analysis.
        return req
    if mode != "normal":
        raise PathPolicyViolation(
            requested_path=req,
            reason=f"unsupported policy mode '{mode}'",
            hint="use mode='normal' or mode='extraordinary_audit'",
        )
    ws_in_generated = _is_relative_to(ws, generated_root)
    ws_in_tmp = (
        _is_relative_to(ws, Path("/tmp").resolve())  # nosec B108
        or _is_relative_to(ws, Path("/var/tmp").resolve())  # nosec B108
        or _is_within_system_temp(ws)
    )
    is_repo_workspace = (ws == repo) and (ws / ".providence").is_dir()
    req_in_repo = _is_relative_to(req, repo)

    if (
        not ws_in_generated
        and not ws_in_tmp
        and not is_repo_workspace
        and not req_in_repo
    ):
        raise PathPolicyViolation(
            requested_path=ws,
            reason="workspace root must be under repository 'generated/' (or /tmp for ephemeral tests), or within repo root",
            hint="use SDD_WORKSPACE_ROOT for a custom path",
        )
    if ws_in_generated and not _is_relative_to(req, generated_root):
        raise PathPolicyViolation(
            requested_path=req,
            reason="normal mode only permits reads under repository 'generated/'",
            hint="enable extraordinary audit mode to read outside generated/",
        )
    if not _is_relative_to(req, ws):
        raise PathPolicyViolation(
            requested_path=req,
            reason="normal mode restricts reads to the active artifact root (X)",
            hint=f"use paths under '{ws}' or provide --workspace-root",
        )
    return req


def compiled_active_dir(root: Path | None = None) -> Path:
    """Compiled Active Dir."""
    workspace_root = resolve_workspace_root(root)
    return workspace_root / ".providence" / "compiled"


def source_semantic_dir(root: Path | None = None) -> Path:
    """Source Semantic Dir."""
    workspace_root = resolve_workspace_root(root)
    return workspace_root / ".providence" / "source"


def profile_active_path(root: Path | None = None) -> Path:
    """Profile Active Path."""
    workspace_root = resolve_workspace_root(root)
    return workspace_root / ".providence" / "profile"
