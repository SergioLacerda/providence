"""Skills registry generator  externalizes skill definitions to .providence/skills/ directory."""

from pathlib import Path
from typing import Any


def generate_skills_registry(output_dir: str, config: dict[str, Any]) -> dict[str, Any]:
    """Generate skill definitions and registry from SkillEngine.

    Writes:
    - .providence/skills/registry.json  index of all skills
    - .providence/skills/<skill_name>/skill.yaml  individual skill definitions
    - .providence/skills/SKILLS.md  human-readable skills documentation

    Args:
        output_dir: Base output directory (workspace root)
        config: Governance configuration dict

    Returns:
        Dict with keys:
            - registry_path: Path to generated registry.json
            - skill_count: Number of skills exported
            - skill_dirs: List of created skill directories
    """
    try:
        from providence_runtime._skill_registry import SkillRegistry
        from providence_runtime.skills import _REGISTRY

        # Use canonical _REGISTRY as source of truth  bypasses stale disk registry.
        skill_registry = SkillRegistry(_REGISTRY, Path("/nonexistent"))
        skills_payload = skill_registry.export_skills_payload(fmt="json")
        skills_list = skills_payload.get("skills", [])

        output_path = Path(output_dir)
        skills_dir = output_path / ".providence" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        # 1. Write individual skill YAML files
        skill_dirs = []
        for skill_dict in skills_list:
            skill_name = skill_dict.get("name", "unknown")
            skill_output_dir = skills_dir / skill_name
            skill_output_dir.mkdir(parents=True, exist_ok=True)

            skill_yaml_file = skill_output_dir / "skill.yaml"

            # Convert dict to YAML string using SkillDefinition
            try:
                from dataclasses import fields

                from providence_runtime.skills import SkillDefinition

                # Build kwargs from dict (only use known fields)
                field_names = {f.name for f in fields(SkillDefinition)}
                skill_kwargs = {k: v for k, v in skill_dict.items() if k in field_names}

                # Create SkillDefinition instance and serialize to YAML
                skill_def = SkillDefinition(**skill_kwargs)
                yaml_content = skill_def.to_yaml()
                skill_yaml_file.write_text(yaml_content, encoding="utf-8")
                skill_dirs.append(str(skill_output_dir))

            except Exception as e:
                import logging

                logging.warning(f"Failed to write skill {skill_name}: {e}")
                continue

        # 2. Write registry.json
        import json

        registry = {
            "schema_version": "1.1.0",
            "skills": [
                {
                    "name": skill.get("name"),
                    "version": skill.get("version"),
                    "category": skill.get("category"),
                    "description": skill.get("description"),
                    "risk_score": skill.get("risk_score"),
                    "status": skill.get("status"),
                    "skill_yaml": f".providence/skills/{skill.get('name')}/skill.yaml",
                }
                for skill in skills_list
            ],
        }

        registry_path = skills_dir / "registry.json"
        registry_path.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 3. Write SKILLS.md documentation
        skills_md = _generate_skills_documentation(skills_list)
        skills_md_path = skills_dir / "SKILLS.md"
        skills_md_path.write_text(skills_md, encoding="utf-8")

        return {
            "registry_path": registry_path.as_posix(),
            "skill_count": len(skills_list),
            "skill_dirs": skill_dirs,
        }

    except ImportError:
        return {
            "registry_path": None,
            "skill_count": 0,
            "skill_dirs": [],
            "error": "SkillEngine not available",
        }


def _generate_skills_documentation(skills: list[dict[str, Any]]) -> str:
    """Generate human-readable skills documentation.

    Args:
        skills: List of skill dictionaries from SkillEngine export

    Returns:
        Markdown documentation string
    """
    lines = [
        "# SDD Skills Registry",
        "",
        "Available skills for governed execution.",
        "",
    ]

    for skill in sorted(skills, key=lambda s: s.get("name", "")):
        name = skill.get("name", "unknown")
        version = skill.get("version", "?")
        category = skill.get("category", "general")
        description = skill.get("description", "No description")
        risk = skill.get("risk_score", "unknown")
        status = skill.get("status", "unknown")

        lines.extend(
            [
                f"## `{name}` v{version}",
                "",
                f"**Category:** {category}  ",
                f"**Risk:** {risk}  ",
                f"**Status:** {status}  ",
                "",
                f"{description}",
                "",
                f"**YAML:** `.providence/skills/{name}/skill.yaml`",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            "## Using Skills",
            "",
            "Load a skill via CLI:",
            "",
            "```bash",
            "sdd skill <name> --execute",
            "```",
            "",
            "Or programmatically:",
            "",
            "```python",
            "from providence_runtime.skills import SkillEngine",
            "engine = SkillEngine()",
            "result = engine.run_skill('diagnose', execute=True)",
            "```",
        ]
    )

    return "\n".join(lines)
