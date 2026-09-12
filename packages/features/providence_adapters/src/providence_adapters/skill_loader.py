"""SkillLoader: reads .providence/skills/ and .providence/commands/ registries."""

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

_SENSITIVE_PATTERNS = re.compile(
    r"(^|[/\\])(\.ssh|\.aws|\.gnupg|\.config/gcloud)[/\\]"
    r"|\.env$|credentials$|id_rsa|id_ed25519|\.pem$|\.key$",
    re.IGNORECASE,
)


def _safe_path(candidate: Path, root: Path) -> Path | None:
    """Return resolved path only if it stays within root and is not sensitive."""
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root.resolve())  # raises ValueError if outside
    except (ValueError, OSError):
        return None
    if _SENSITIVE_PATTERNS.search(str(resolved)):
        return None
    return resolved


class SkillLoader:
    """Loads skills and commands from .providence/ registries."""

    def load_skills(self, sdd_dir: Path) -> list[dict[str, Any]]:
        """
        Load all skills from .providence/skills/registry.json and their YAML files.

        Args:
            sdd_dir: path to .providence/

        Returns:
            list of skill dicts with full metadata
        """
        registry_path = sdd_dir / "skills" / "registry.json"

        if not registry_path.exists():
            return []

        with open(registry_path, encoding="utf-8", errors="strict") as f:
            registry = json.load(f)

        skills = []
        for skill_entry in registry.get("skills", []):
            skill_name = skill_entry.get("name")
            skill_dir = sdd_dir / "skills" / skill_name
            skill_yaml_path = skill_dir / "skill.yaml"

            safe_yaml = _safe_path(skill_yaml_path, sdd_dir)
            if safe_yaml and safe_yaml.exists():
                with open(
                    os.path.realpath(safe_yaml), encoding="utf-8", errors="strict"
                ) as f:
                    skill_yaml = yaml.safe_load(f)
                # Merge registry entry with YAML content
                skill = {**skill_entry, **skill_yaml}
                # Load SKILL.md if present â€” enriches adapter rendering
                skill_md_path = skill_dir / "SKILL.md"
                safe_md = _safe_path(skill_md_path, sdd_dir)
                if safe_md and safe_md.exists():
                    skill["skill_md"] = safe_md.read_text(encoding="utf-8")
                skills.append(skill)

        return skills

    def load_commands(self, sdd_dir: Path) -> list[dict[str, Any]]:
        """
        Load all commands from .providence/commands/registry.json and their YAML files.

        Args:
            sdd_dir: path to .providence/

        Returns:
            list of command dicts with full metadata
        """
        registry_path = sdd_dir / "commands" / "registry.json"

        if not registry_path.exists():
            return []

        with open(registry_path, encoding="utf-8", errors="strict") as f:
            registry = json.load(f)

        commands = []
        for cmd_entry in registry.get("commands", []):
            cmd_id = cmd_entry.get("id")
            cmd_yaml_path = sdd_dir / "commands" / cmd_id / "command.yaml"

            safe_cmd = _safe_path(cmd_yaml_path, sdd_dir)
            if safe_cmd and safe_cmd.exists():
                with open(
                    os.path.realpath(safe_cmd), encoding="utf-8", errors="strict"
                ) as f:
                    cmd_yaml = yaml.safe_load(f)
                # Merge registry entry with YAML content
                command = {**cmd_entry, **cmd_yaml}
                commands.append(command)

        return commands
