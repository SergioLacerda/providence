"""CLI-facing wrappers over canonical runtime skill registry."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from providence_runtime import SkillDefinition, SkillEngine


def _get_workspace_root() -> Path:
    """Resolve workspace root, falling back to cwd if not found."""
    try:
        from providence_core.utils.environment import find_workspace_root

        root = find_workspace_root()
        if root:
            return root
    except Exception as e:
        logging.debug("workspace root resolution failed: %s", e)
    return Path.cwd()


def list_skills() -> list[SkillDefinition]:
    """List Skills."""
    engine = SkillEngine(project_root=_get_workspace_root())
    return engine.list_skills()


def get_skill(name: str) -> SkillDefinition | None:
    """Get Skill."""
    engine = SkillEngine(project_root=_get_workspace_root())
    return engine.get_skill(name)


def export_skills_payload(fmt: str) -> dict[str, Any]:
    """Export Skills Payload."""
    engine = SkillEngine(project_root=_get_workspace_root())
    return engine.export_skills_payload(fmt)
