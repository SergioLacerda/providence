"""Public API boundary for providence_core.

Avoid importing heavyweight modules at package import time so utility-only
callers (e.g. process wrappers in CI bootstrap) don't require compiler deps.
"""

from typing import TYPE_CHECKING, Any

from providence_core.utils.environment import (
    ProfileContext,
    WorkspaceNotInitializedError,
    detect_repo_root,
    get_sdd_paths,
    resolve_profile,
)

if TYPE_CHECKING:
    from providence_core.deployment_manager import (
        DeploymentManager as DeploymentManager,
    )
    from providence_core.governance_orchestrator import (
        GovernanceOrchestrator as GovernanceOrchestrator,
    )
else:
    DeploymentManager: Any
    GovernanceOrchestrator: Any

__all__ = [
    "DeploymentManager",
    "GovernanceOrchestrator",
    "ProfileContext",
    "WorkspaceNotInitializedError",
    "detect_repo_root",
    "get_sdd_paths",
    "resolve_profile",
]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    if name == "DeploymentManager":
        from providence_core.deployment_manager import DeploymentManager

        return DeploymentManager
    if name == "GovernanceOrchestrator":
        from providence_core.governance_orchestrator import GovernanceOrchestrator

        return GovernanceOrchestrator
    raise AttributeError(f"module 'providence_core' has no attribute {name!r}")
