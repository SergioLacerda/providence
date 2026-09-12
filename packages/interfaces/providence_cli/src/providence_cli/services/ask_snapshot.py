"""Shared governed ask snapshot builder for ask/pipeline entrypoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_governed_ask_snapshot(
    *,
    query: str,
    skill: str | None,
    organize_used: bool,
    workspace_root: Path | None = None,
    require_handshake: bool = True,
) -> dict[str, Any]:
    """Compatibility wrapper for governed ask snapshot builder."""
    from providence_cli.commands import _ask_backend

    return _ask_backend.build_governed_ask_snapshot(
        query=query,
        skill=skill,
        organize_used=organize_used,
        workspace_root=workspace_root,
        require_handshake=require_handshake,
    )
