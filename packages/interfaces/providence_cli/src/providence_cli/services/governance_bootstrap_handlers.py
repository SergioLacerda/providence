"""Bootstrap handshake and signing handlers for `providence governance generate`."""

from __future__ import annotations

from typing import Any

from providence_cli.services._governance_generate_support import (
    bootstrap_response,
    run_bootstrap_signing_flow,
)
from providence_cli.utils.providence_authority import resolve_workspace_root


def complete_bootstrap_handshake() -> None:
    """Run and complete the agent handshake protocol for bootstrap.

    Uses `resolve_workspace_root()` explicitly rather than relying on
    `AgentHandshakeProtocol()`'s cwd-based default resolution, so this
    always targets the same workspace as the rest of the bootstrap flow
    (and honors `SDD_WORKSPACE_ROOT` in isolated test/CI environments
    instead of silently falling back to the process cwd).
    """
    from providence_core.governance.handshake import AgentHandshakeProtocol

    ahp = AgentHandshakeProtocol(project_root=resolve_workspace_root())
    challenge = ahp.generate_challenge(task_description="Bootstrap Session")
    ahp.complete_handshake(bootstrap_response(challenge))


def run_bootstrap_signing(key_id: str, *, keygen_fn: Any, sign_fn: Any) -> None:
    """Run the bootstrap key generation and signing flow."""
    run_bootstrap_signing_flow(
        key_id,
        keygen_fn=keygen_fn,
        sign_fn=sign_fn,
        resolve_workspace_root_fn=resolve_workspace_root,
    )
