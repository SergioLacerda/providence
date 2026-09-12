#!/usr/bin/env python3
"""Resolve personal agent capabilities overlaid with canonical .providence registries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DriftEvent:
    code: str
    message: str
    path: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "path": self.path}


def _load_json(path: Path) -> tuple[dict[str, Any] | None, DriftEvent | None]:
    if not path.exists():
        return None, DriftEvent("missing_file", "required file not found", str(path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, DriftEvent("invalid_json", "failed to parse json file", str(path))
    if not isinstance(data, dict):
        return None, DriftEvent("invalid_schema", "json root must be object", str(path))
    return data, None


def _discover_personal_skills(source_root: Path) -> list[dict[str, Any]]:
    skills_dir = source_root / "skills"
    if not skills_dir.exists():
        return []
    discovered: list[dict[str, Any]] = []
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        discovered.append(
            {
                "name": skill_file.parent.name,
                "source": str(source_root),
                "path": str(skill_file),
                "kind": "personal",
            }
        )
    return discovered


def _validate_skill_canonical(
    project_root: Path, skill_entry: dict[str, Any]
) -> DriftEvent | None:
    yaml_path = skill_entry.get("skill_yaml")
    if not isinstance(yaml_path, str) or not yaml_path:
        return DriftEvent(
            "missing_canonical_ref",
            "skill entry missing skill_yaml reference",
            ".providence/skills/registry.json",
        )
    canonical_path = project_root / yaml_path
    if canonical_path.exists():
        return None
    return DriftEvent(
        "missing_canonical_file",
        "skill canonical file referenced by registry does not exist",
        str(canonical_path),
    )


def _validate_command_canonical(
    project_root: Path, command_entry: dict[str, Any]
) -> DriftEvent | None:
    command_id = command_entry.get("id")
    if not isinstance(command_id, str) or not command_id:
        return DriftEvent(
            "invalid_command_id",
            "command entry missing id",
            ".providence/commands/registry.json",
        )
    canonical_path = (
        project_root / ".providence" / "commands" / command_id / "command.yaml"
    )
    if canonical_path.exists():
        return None
    return DriftEvent(
        "missing_canonical_file",
        "command canonical file referenced by registry does not exist",
        str(canonical_path),
    )


def _load_skills_from_registry(
    project_root: Path,
    registry_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Load governed skills from the .providence skills registry. Returns (skills, drift_events)."""
    skills: list[dict[str, Any]] = []
    drift: list[dict[str, str]] = []
    registry, err = _load_json(registry_path)
    if err:
        drift.append(err.as_dict())
        return skills, drift
    assert registry is not None
    raw = registry.get("skills", [])
    if not isinstance(raw, list):
        drift.append(
            DriftEvent(
                "invalid_schema",
                "skills registry must include list under skills",
                str(registry_path),
            ).as_dict()
        )
        return skills, drift
    for entry in raw:
        if not (isinstance(entry, dict) and isinstance(entry.get("name"), str)):
            continue
        canonical_err = _validate_skill_canonical(project_root, entry)
        if canonical_err:
            drift.append(canonical_err.as_dict())
            continue
        skills.append(
            {
                "name": entry["name"],
                "source": ".providence",
                "path": entry.get("skill_yaml", ""),
                "kind": "governed",
            }
        )
    return skills, drift


def _load_commands_from_registry(
    project_root: Path,
    registry_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Load governed commands from the .providence commands registry. Returns (commands, drift_events)."""
    commands: list[dict[str, Any]] = []
    drift: list[dict[str, str]] = []
    registry, err = _load_json(registry_path)
    if err:
        drift.append(err.as_dict())
        return commands, drift
    assert registry is not None
    raw = registry.get("commands", [])
    if not isinstance(raw, list):
        drift.append(
            DriftEvent(
                "invalid_schema",
                "commands registry must include list under commands",
                str(registry_path),
            ).as_dict()
        )
        return commands, drift
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        canonical_err = _validate_command_canonical(project_root, entry)
        if canonical_err:
            drift.append(canonical_err.as_dict())
            continue
        commands.append(entry)
    return commands, drift


def resolve_personal_overlay(
    *,
    project_root: Path,
    personal_root_candidates: list[Path] | None = None,
) -> dict[str, Any]:
    """Resolve effective agent capabilities using local personal + .providence overlays."""
    project_root = Path(project_root)
    if personal_root_candidates is None:
        personal_root_candidates = [
            project_root / ".agents",
            Path.home() / ".agents",
        ]

    skills_local: list[dict[str, Any]] = []
    personal_sources: list[str] = []
    for root in personal_root_candidates:
        if root.exists():
            personal_sources.append(str(root))
            skills_local.extend(_discover_personal_skills(root))

    skills_registry_path = project_root / ".providence" / "skills" / "registry.json"
    commands_registry_path = project_root / ".providence" / "commands" / "registry.json"

    skills_sdd, drift_skills = _load_skills_from_registry(
        project_root, skills_registry_path
    )
    commands_sdd, drift_commands = _load_commands_from_registry(
        project_root, commands_registry_path
    )
    drift_events = drift_skills + drift_commands

    # Dedupe local skills first, then overlay governed skills over same name.
    effective_skills_by_name = {skill["name"]: skill for skill in skills_local}
    conflicts: list[dict[str, str]] = []
    for governed in skills_sdd:
        existing = effective_skills_by_name.get(governed["name"])
        if existing and existing.get("source") != governed["source"]:
            conflicts.append(
                {
                    "type": "skill_name_conflict",
                    "name": governed["name"],
                    "winner": ".providence",
                    "loser": existing.get("source", "unknown"),
                }
            )
        effective_skills_by_name[governed["name"]] = governed

    return {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "personal_sources": personal_sources,
        "sdd_sources": {
            "skills_registry": str(skills_registry_path),
            "commands_registry": str(commands_registry_path),
        },
        "skills_local": skills_local,
        "skills_sdd": skills_sdd,
        "commands_sdd": commands_sdd,
        "effective_skills": sorted(
            effective_skills_by_name.values(), key=lambda item: item["name"]
        ),
        "effective_commands": commands_sdd,
        "conflicts": conflicts,
        "drift_events": drift_events,
    }
