"""SkillEngine — thin facade over SkillRegistry + SkillExecutor."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from providence_skills import SkillRunResult

from .._skill_contracts import SkillDefinition
from .._skill_executor import SkillExecutor
from .._skill_registry import SkillRegistry
from ._registry_data import _REGISTRY

if TYPE_CHECKING:
    from ..telemetry import TelemetrySink


class SkillEngine:
    """Canonical runtime executor for capability-oriented operations."""

    def __init__(
        self,
        sink: TelemetrySink | None = None,
        project_root: Path | str | None = None,
    ) -> None:
        if project_root is None:
            root = Path.cwd()
        elif isinstance(project_root, str):
            root = Path(project_root)
        else:
            root = project_root
        self._registry = SkillRegistry(_REGISTRY, root)
        self._executor = SkillExecutor(self._registry, sink)

    def list_skills(self) -> list[SkillDefinition]:
        """List Skills."""
        return self._registry.list_skills()

    def get_skill(self, name: str) -> SkillDefinition | None:
        """Get Skill."""
        return self._registry.get_skill(name)

    def export_skills_payload(self, fmt: str) -> dict[str, Any]:
        """Export Skills Payload."""
        return self._registry.export_skills_payload(fmt)

    def run_skill(
        self,
        name: str,
        *,
        execute: bool = False,
        profile: str = "default",
        enforcement_mode: str = "warn",
        project_root: Path | None = None,
        context: dict[str, Any] | None = None,
    ) -> SkillRunResult:
        """Run a registered skill through the runtime executor."""
        return self._executor.run_skill(
            name,
            execute=execute,
            profile=profile,
            enforcement_mode=enforcement_mode,
            project_root=project_root,
            context=context,
        )
