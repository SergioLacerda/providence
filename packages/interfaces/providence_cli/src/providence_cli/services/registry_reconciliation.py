"""Canonical registry reconciliation (disk -> registry)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required for registry reconciliation") from exc

from providence_cli.services._registry_models import (
    ReconciliationError,
    ReconciliationSummary,
)

__all__ = ["ReconciliationError", "ReconciliationSummary", "reconcile_registries"]


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=str(path.parent), suffix=".tmp"
    ) as tmp:
        json.dump(payload, tmp, indent=2, ensure_ascii=False)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _load_existing_entries(registry_path: Path, key: str) -> list[dict[str, Any]]:
    if not registry_path.exists():
        return []
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    entries = data.get(key)
    if not isinstance(entries, list):
        raise ReconciliationError(f"invalid registry format in {registry_path}")
    return [entry for entry in entries if isinstance(entry, dict)]


def _required(
    payload: dict[str, Any], required_fields: tuple[str, ...], source: Path
) -> None:
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise ReconciliationError(
            f"missing required field(s) {missing} in canonical file: {source}"
        )


def _reconcile_commands(workspace_root: Path) -> tuple[dict[str, Any], dict[str, int]]:
    commands_dir = workspace_root / ".providence" / "commands"
    registry_path = commands_dir / "registry.json"

    existing = _load_existing_entries(registry_path, "commands")
    existing_ids = {str(item.get("id", "")) for item in existing if item.get("id")}

    command_entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_slashes: set[str] = set()

    canonical_files = sorted(commands_dir.glob("*/command.yaml"))
    for file_path in canonical_files:
        payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ReconciliationError(f"invalid YAML object in {file_path}")

        _required(payload, ("id", "slash", "routes_to"), file_path)

        cmd_id = str(payload["id"])
        slash = str(payload["slash"])
        routes_to = payload["routes_to"]
        targets = payload.get("targets", payload.get("adapter_targets", []))

        if not isinstance(routes_to, dict):
            raise ReconciliationError(f"routes_to must be object in {file_path}")
        if not isinstance(targets, list):
            raise ReconciliationError(f"targets must be list in {file_path}")

        if cmd_id in seen_ids:
            raise ReconciliationError(f"duplicate command id detected: {cmd_id}")
        if slash in seen_slashes:
            raise ReconciliationError(f"duplicate command slash detected: {slash}")

        seen_ids.add(cmd_id)
        seen_slashes.add(slash)

        command_entries.append(
            {
                "id": cmd_id,
                "slash": slash,
                "routes_to": routes_to,
                "targets": [str(target) for target in targets],
            }
        )

    command_entries.sort(key=lambda item: str(item["id"]))
    new_registry = {"schema_version": "1.0.0", "commands": command_entries}

    canonical_ids = {str(item["id"]) for item in command_entries}
    stats = {
        "added": len(canonical_ids - existing_ids),
        "removed": len(existing_ids - canonical_ids),
        "unchanged": len(canonical_ids & existing_ids),
    }
    return new_registry, stats


def _reconcile_skills(workspace_root: Path) -> tuple[dict[str, Any], dict[str, int]]:
    skills_dir = workspace_root / ".providence" / "skills"
    registry_path = skills_dir / "registry.json"

    existing = _load_existing_entries(registry_path, "skills")
    existing_names = {
        str(item.get("name", "")) for item in existing if item.get("name")
    }

    skill_entries: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    canonical_files = sorted(skills_dir.glob("*/skill.yaml"))
    for file_path in canonical_files:
        payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ReconciliationError(f"invalid YAML object in {file_path}")

        _required(
            payload,
            ("name", "version", "category", "description", "status"),
            file_path,
        )

        name = str(payload["name"])
        if name in seen_names:
            raise ReconciliationError(f"duplicate skill name detected: {name}")
        seen_names.add(name)

        skill_entries.append(
            {
                "name": name,
                "version": str(payload["version"]),
                "category": str(payload["category"]),
                "description": str(payload["description"]),
                "risk_score": payload.get("risk_score"),
                "status": str(payload["status"]),
                "skill_yaml": f".providence/skills/{name}/skill.yaml",
            }
        )

    skill_entries.sort(key=lambda item: str(item["name"]))
    new_registry = {"schema_version": "1.1.0", "skills": skill_entries}

    canonical_names = {str(item["name"]) for item in skill_entries}
    stats = {
        "added": len(canonical_names - existing_names),
        "removed": len(existing_names - canonical_names),
        "unchanged": len(canonical_names & existing_names),
    }
    return new_registry, stats


def reconcile_registries(
    workspace_root: Path, *, check_only: bool = False
) -> ReconciliationSummary:
    """Regenerate command/skill registries from canonical disk artifacts."""
    commands_registry, command_stats = _reconcile_commands(workspace_root)
    skills_registry, skill_stats = _reconcile_skills(workspace_root)

    drift_detected = (
        command_stats.get("added", 0) > 0
        or command_stats.get("removed", 0) > 0
        or skill_stats.get("added", 0) > 0
        or skill_stats.get("removed", 0) > 0
    )

    if not check_only:
        _atomic_write_json(
            workspace_root / ".providence" / "commands" / "registry.json",
            commands_registry,
        )
        _atomic_write_json(
            workspace_root / ".providence" / "skills" / "registry.json", skills_registry
        )
    return ReconciliationSummary(
        commands=command_stats, skills=skill_stats, drift_detected=drift_detected
    )
