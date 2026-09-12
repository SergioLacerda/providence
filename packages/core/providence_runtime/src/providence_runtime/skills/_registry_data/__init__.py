"""Hardcoded fallback skill registry definitions."""

from __future__ import annotations

from ..._skill_contracts import SkillDefinition
from ._analysis import _ANALYSIS_SKILLS
from ._correction import _CORRECTION_SKILLS
from ._operations import _OPERATIONS_SKILLS
from ._orchestration import _ORCHESTRATION_SKILLS

_REGISTRY: dict[str, SkillDefinition] = {
    **_ORCHESTRATION_SKILLS,
    **_ANALYSIS_SKILLS,
    **_OPERATIONS_SKILLS,
    **_CORRECTION_SKILLS,
}

__all__ = ["_REGISTRY"]
