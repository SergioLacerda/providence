"""Index generators  externalizes searchable indices to .providence/indices/ directory."""

import json
from pathlib import Path
from typing import Any, cast

from providence_cli.generators._cli_commands_index import (
    _timestamp_iso8601,
    generate_cli_commands_index,
)

__all__ = ["generate_cli_commands_index", "generate_skill_index"]


def generate_skill_index(output_dir: str, config: dict[str, Any]) -> dict[str, Any]:
    """Generate skill discovery index.

    Writes:
    - .providence/indices/skills.index.json  searchable skill metadata

    Args:
        output_dir: Base output directory (workspace root)
        config: Governance configuration dict

    Returns:
        Dict with keys:
            - index_path: Path to generated skills.index.json
            - skill_count: Number of skills indexed
            - indexed_skills: List of indexed skill names
    """
    try:
        from providence_runtime.skills import SkillEngine

        engine = SkillEngine()
        skills = engine.list_skills()

        output_path = Path(output_dir)
        indices_dir = output_path / ".providence" / "indices"
        indices_dir.mkdir(parents=True, exist_ok=True)

        skills_index = {
            "schema_version": "1.0.0",
            "index_type": "skills",
            "generated_at": _timestamp_iso8601(),
            "skills": [
                {
                    "name": skill.name,
                    "category": skill.category,
                    "description": skill.description,
                    "version": skill.version,
                    "status": skill.status,
                    "risk_score": skill.risk_score,
                    "executable_via_cli": bool(skill.cli_fallback),
                    "required_permissions": skill.required_permissions or [],
                    "budget_policy": skill.budget_policy or {},
                    "yaml_path": f".providence/skills/{skill.name}/skill.yaml",
                }
                for skill in sorted(skills, key=lambda s: s.name)
            ],
        }

        index_path = indices_dir / "skills.index.json"
        index_path.write_text(
            json.dumps(skills_index, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        indexed_skills: list[str] = [
            cast(dict[str, Any], skill)["name"]
            for skill in cast(list[Any], skills_index["skills"])
        ]

        return {
            "index_path": index_path.as_posix(),
            "skill_count": len(indexed_skills),
            "indexed_skills": indexed_skills,
        }

    except ImportError:
        return {
            "index_path": None,
            "skill_count": 0,
            "indexed_skills": [],
            "error": "SkillEngine not available",
        }
