"""SkillExecutor — execution engine for governed skill runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from providence_skills import SkillRunResult

from .._skill_registry import SkillRegistry
from ..telemetry import TelemetrySink
from ._executor_footer import resolve_footer_policy
from ._executor_run import run_skill_flow
from ._executor_telemetry import emit_skill_telemetry


class SkillExecutor:
    """Execution facade for skills. Delegates orchestration to helper modules."""

    def __init__(
        self,
        registry: SkillRegistry,
        sink: TelemetrySink | None = None,
    ) -> None:
        self._registry = registry
        self._sink = sink

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
        result = run_skill_flow(
            registry=self._registry,
            sink=self._sink,
            run_skill=self.run_skill,
            name=name,
            execute=execute,
            profile=profile,
            enforcement_mode=enforcement_mode,
            project_root=project_root,
            context=context,
            footer_policy=resolve_footer_policy(project_root),
        )
        emit_skill_telemetry(self._sink, result)
        return result
