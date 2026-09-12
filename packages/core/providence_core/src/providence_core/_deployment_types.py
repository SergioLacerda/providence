from __future__ import annotations

from typing import Any, TypedDict


class DeploymentResult(TypedDict):
    success: bool
    deployed_files: dict[str, str]
    deployment_location: str
    checklist: dict[str, bool]
    manifest: dict[str, Any]
    next_steps: list[str]
