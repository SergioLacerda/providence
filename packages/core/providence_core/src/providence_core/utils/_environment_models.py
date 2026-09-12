"""Profile models for SDD workspace resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

SddProfile = Literal["master", "client"]


class WorkspaceNotInitializedError(RuntimeError):
    """Raised when no `.providence/profile` is found and no override is provided."""

    def __init__(self, start: Path) -> None:
        super().__init__(
            f"No SDD workspace found from '{start}' up to filesystem root.\n"
            "Run 'providence init' to initialize a workspace, or use --profile / "
            "SDD_PROFILE to override."
        )


@dataclass(frozen=True)
class ProfileContext:
    """Resolved workspace profile context."""

    type: SddProfile
    name: str
    workspace_id: str
    core_hash: str
    root: Path
    language: str | None = None

    @property
    def is_master(self) -> bool:
        return self.type == "master"

    @property
    def is_client(self) -> bool:
        return self.type == "client"

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile": self.type,
            "name": self.name,
            "workspace_id": self.workspace_id,
            "core_hash": self.core_hash,
            "root": self.root,
            "is_master": self.is_master,
            "is_client": self.is_client,
            "language": self.language,
        }
