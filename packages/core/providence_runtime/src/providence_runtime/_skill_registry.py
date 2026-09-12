"""Skill registry — loads, stores, and looks up SkillDefinition objects."""

from __future__ import annotations

import json
import logging
from dataclasses import fields as dataclass_fields
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

from ._skill_contracts import SkillDefinition

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Owns skill storage and lookup. No execution or telemetry concerns."""

    def __init__(
        self,
        fallback: dict[str, SkillDefinition],
        project_root: Path,
    ) -> None:
        self._fallback = fallback
        self._skills: dict[str, SkillDefinition] = {}
        self._registry_source = "hardcoded"
        self._load_skills_from_disk(project_root)
        if not self._skills:
            self._skills = dict(fallback)
            self._registry_source = "hardcoded"

    def _load_skills_from_disk(self, project_root: Path) -> None:
        skills_dir = project_root / ".providence" / "skills"
        if not skills_dir.exists():
            return
        try:
            registry_file = skills_dir / "registry.json"
            if registry_file.exists():
                registry_data = json.loads(registry_file.read_text(encoding="utf-8"))
                for skill_meta in registry_data.get("skills", []):
                    skill_name = skill_meta.get("name")
                    if not isinstance(
                        skill_name, str
                    ) or not self._is_canonical_skill_name(skill_name):
                        continue
                    skill_yaml_path = skills_dir / skill_name / "skill.yaml"
                    if skill_yaml_path.exists() and yaml is not None:
                        try:
                            skill_dict = yaml.safe_load(
                                skill_yaml_path.read_text(encoding="utf-8")
                            )
                            if skill_dict:
                                field_names = {
                                    f.name for f in dataclass_fields(SkillDefinition)
                                }
                                skill_def = SkillDefinition(
                                    **{
                                        k: v
                                        for k, v in skill_dict.items()
                                        if k in field_names
                                    }
                                )
                                self._skills[skill_name] = skill_def
                        except Exception:  # nosec B112
                            continue
            if self._skills:
                self._registry_source = "file"
        except Exception:  # nosec B110
            pass

    @staticmethod
    def _is_canonical_skill_name(name: str) -> bool:
        return name.startswith("sdd-")

    def list_skills(self) -> list[SkillDefinition]:
        """Return deduplicated, sorted list of canonical skills."""
        seen: dict[str, SkillDefinition] = {}
        for skill in self._skills.values():
            if skill.name not in seen:
                seen[skill.name] = skill
        return sorted(seen.values(), key=lambda s: s.name)

    def get_skill(self, name: str) -> SkillDefinition | None:
        """Accept canonical (sdd-diagnose) or short (diagnose) names.

        When registry_source is hardcoded, reads from the live fallback dict so
        tests that mutate it after construction see the updated values.
        """
        registry = (
            self._fallback if self._registry_source == "hardcoded" else self._skills
        )
        skill = registry.get(name)
        if skill is None and not name.startswith("sdd-"):
            skill = registry.get(f"sdd-{name}")
        return skill

    def export_skills_payload(self, fmt: str) -> dict[str, Any]:
        """Export all skills in the specified format."""
        skills = [skill.to_dict() for skill in self.list_skills()]
        if fmt == "json":
            return {"schema_version": "1.1.0", "skills": skills}
        if fmt == "openai":
            return {
                "schema_version": "1.1.0",
                "format": "openai",
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": s["name"].replace("-", "_"),
                            "description": s["description"],
                            "parameters": {
                                "type": "object",
                                "properties": {"input": {"type": "string"}},
                                "required": ["input"],
                            },
                        },
                    }
                    for s in skills
                ],
            }
        if fmt == "langchain":
            return {
                "schema_version": "1.1.0",
                "format": "langchain",
                "tools": [
                    {
                        "name": s["name"].replace("-", "_"),
                        "description": s["description"],
                        "args": {
                            "input": {
                                "type": "string",
                                "description": f"Input for {s['name']} skill",
                            }
                        },
                    }
                    for s in skills
                ],
            }
        if fmt == "crewai":
            return {
                "schema_version": "1.1.0",
                "format": "crewai",
                "tools": [
                    {
                        "name": s["name"].replace("-", "_"),
                        "description": s["description"],
                        "tool_input": {
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }
                    for s in skills
                ],
            }
        if fmt == "autogen":
            return {
                "schema_version": "1.1.0",
                "format": "autogen",
                "functions": [
                    {
                        "name": s["name"].replace("-", "_"),
                        "description": s["description"],
                        "parameters": {
                            "type": "object",
                            "properties": {"input": {"type": "string"}},
                            "required": ["input"],
                        },
                    }
                    for s in skills
                ],
            }
        return {
            "schema_version": "1.1.0",
            "format": fmt,
            "skills": skills,
            "note": "Adapter metadata generated from canonical runtime registry.",
        }
