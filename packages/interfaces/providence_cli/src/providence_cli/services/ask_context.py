"""Workspace context loading for providence ask  primary entry point: `load_ask_context`."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from providence_cli.services.ask_governance import GovResult
from providence_cli.services.ask_governance import (
    load_compiled_governance as _load_compiled_governance_impl,
)
from providence_cli.services.ask_governance import (
    load_governance_via_runtime as _load_governance_via_runtime,
)
from providence_cli.utils.providence_authority import (
    compiled_active_dir,
    enforce_path_policy,
    profile_active_path,
)
from providence_cli.utils.providence_authority import (
    resolve_workspace_root as _resolve_authority_workspace_root,
)

logger = logging.getLogger(__name__)

_GOV_CACHE: dict[str, GovResult] = {}


@dataclass(frozen=True)
class AskContext:
    """Resolved workspace context for a single ask invocation."""

    workspace_root: Path
    profile: str
    ahp_state: str
    context_source: str
    fingerprint: str
    mandates_count: int
    authenticated: bool
    degraded: bool
    degrade_reason: str
    trust_source: str
    drift_detected: bool
    root_seed_drift_detected: bool


class WorkspaceNotFoundError(Exception):
    """Raised when the SDD workspace root cannot be resolved."""


def resolve_workspace_root() -> Path:
    """Resolve and validate the SDD workspace root path."""
    root = _resolve_authority_workspace_root()
    return enforce_path_policy(root, workspace_root=root, mode="normal")


def get_cached_ahp() -> dict[str, Any] | None:
    """Return the AHP result cached in the current Click context, if available."""
    try:
        import click

        ctx = click.get_current_context(silent=True)
        if ctx is not None and isinstance(ctx.obj, dict):
            cached = ctx.obj.get("_ahp")
            if isinstance(cached, dict):
                return cached
    except (ImportError, RuntimeError):
        return None
    return None


def get_profile_state(workspace_root: Path) -> tuple[str, str]:
    """Return (profile, state) best-effort; never raises."""
    profile = ""
    profile_path = profile_active_path(workspace_root)
    if profile_path.exists():
        try:
            import configparser

            parser = configparser.ConfigParser()
            parser.read(profile_path)
            profile = parser.get("sdd", "type", fallback="").strip()
        except Exception:
            profile = ""
    cached_ahp = get_cached_ahp()
    if cached_ahp is not None:
        return profile or "default", str(cached_ahp.get("state", "UNKNOWN"))
    try:
        from providence_core.governance.handshake import AgentHandshakeProtocol

        ahp = AgentHandshakeProtocol(project_root=workspace_root)
        state, _ = ahp.validate(output_mode="silent")
        return profile or "default", state
    except Exception:
        return profile or "default", "UNKNOWN"


def load_compiled_governance(workspace_root: Path) -> GovResult:
    """Load compiled governance config from cache or disk."""
    key = str(workspace_root.resolve())
    cached = _GOV_CACHE.get(key)
    if cached is not None:
        return cached
    result = _load_compiled_governance_impl(
        workspace_root,
        compiled_active_dir_fn=compiled_active_dir,
        logger=logger,
        load_via_runtime_fn=_load_governance_via_runtime,
    )
    _GOV_CACHE[key] = result
    return result


def load_ask_context(
    workspace_root: Path | None = None, profile: str | None = None
) -> AskContext:
    """Load and return the complete workspace context for an ask invocation.

    Raises WorkspaceNotFoundError if the workspace root does not exist.
    """
    from providence_cli.services.ask_context_drift import (
        check_fingerprint_drift,
        check_root_seed_drift,
    )

    root = workspace_root or resolve_workspace_root()
    if not root.exists():
        raise WorkspaceNotFoundError(f"Workspace root not found: {root}")

    resolved_profile, ahp_state = get_profile_state(root)
    effective_profile = profile or resolved_profile

    (
        context_source,
        fingerprint,
        mandates_count,
        authenticated,
        degraded,
        degrade_reason,
        trust_source,
    ) = load_compiled_governance(root)

    drift_detected = check_fingerprint_drift(root, fingerprint)
    root_seed_drift_detected = check_root_seed_drift(root)

    return AskContext(
        workspace_root=root,
        profile=effective_profile,
        ahp_state=ahp_state,
        context_source=context_source,
        fingerprint=fingerprint,
        mandates_count=mandates_count,
        authenticated=authenticated,
        degraded=degraded,
        degrade_reason=degrade_reason,
        trust_source=trust_source,
        drift_detected=drift_detected,
        root_seed_drift_detected=root_seed_drift_detected,
    )
