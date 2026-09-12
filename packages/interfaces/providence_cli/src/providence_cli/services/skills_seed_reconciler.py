"""Root seed-artifact reconciliation: prune stale generated prompt/skill files."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


def _read_registry_ids(registry_path: Path, key: str, id_key: str) -> list[str]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    rows = data.get(key, [])
    if not isinstance(rows, list):
        raise ValueError(f"invalid registry format for {registry_path}")
    ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = str(row.get(id_key, "")).strip()
        if value:
            ids.append(value)
    return ids


def _prune_managed_files(
    dir_path: Path,
    expected_names: set[str],
    pattern: str,
    stats: dict[str, int],
    *,
    dry_run: bool,
) -> None:
    if not dir_path.exists():
        return
    for path in dir_path.glob(pattern):
        if path.name not in expected_names:
            stats["would_delete"] += 1
            if not dry_run:
                path.unlink(missing_ok=True)
                stats["deleted"] += 1


def _prune_antigravity_skills(
    root: Path, skill_names: set[str], stats: dict[str, int], *, dry_run: bool
) -> None:
    antigravity_skills_dir = root / ".gemini" / "antigravity" / "skills"
    if not antigravity_skills_dir.exists():
        return
    protected = {"sdd-governance", "providence"}
    for path in antigravity_skills_dir.iterdir():
        if not path.is_dir():
            continue
        if path.name in skill_names or path.name in protected:
            continue
        stats["would_delete"] += 1
        if not dry_run:
            shutil.rmtree(path)
            stats["deleted"] += 1


def _reconcile_root_seed_artifacts(
    root: Path, *, dry_run: bool = False
) -> dict[str, int]:
    commands_registry = root / ".providence" / "commands" / "registry.json"
    skills_registry = root / ".providence" / "skills" / "registry.json"
    missing = [str(p) for p in (commands_registry, skills_registry) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "missing canonical registry file(s): " + ", ".join(missing)
        )

    command_ids = set(
        _read_registry_ids(commands_registry, key="commands", id_key="id")
    )
    skill_names = set(_read_registry_ids(skills_registry, key="skills", id_key="name"))

    expected_prompt_files = {f"{cmd_id}.prompt.md" for cmd_id in command_ids}
    expected_claude_command_files = {f"{cmd_id}.md" for cmd_id in command_ids}
    stats: dict[str, int] = {"deleted": 0, "would_delete": 0}

    _prune_managed_files(
        root / ".github" / "prompts",
        expected_prompt_files,
        "*.prompt.md",
        stats,
        dry_run=dry_run,
    )
    _prune_managed_files(
        root / ".codex" / "skills",
        expected_prompt_files,
        "*.prompt.md",
        stats,
        dry_run=dry_run,
    )
    _prune_managed_files(
        root / ".claude" / "commands",
        expected_claude_command_files,
        "sdd-*.md",
        stats,
        dry_run=dry_run,
    )
    _prune_antigravity_skills(root, skill_names, stats, dry_run=dry_run)
    return stats
