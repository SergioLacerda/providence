"""Commands registry generator  creates .providence/commands/ with CLI and skill-routed commands."""

import json
from pathlib import Path
from typing import Any

# Canonical command registry: skill-routed + CLI-routed commands.
# Skill-routed commands are derived from _REGISTRY in providence_runtime.skills.
# CLI-routed commands wrap sdd CLI primitives as agent slash commands.
_CLI_COMMANDS = [
    {
        "id": "sdd-ask",
        "slash": "/sdd-ask",
        "routes_to": {"type": "cli", "command": "providence ask"},
        "description": "Query Providence governance context. Minimal governed query against compiled context.",
        "targets": ["claude", "codex", "copilot", "antigravity"],
    },
    {
        "id": "sdd-organize",
        "slash": "/sdd-organize",
        "routes_to": {"type": "cli", "command": "providence organize"},
        "description": "Index and prepare large context blocks for efficient retrieval before analysis.",
        "targets": ["claude", "codex", "copilot", "antigravity"],
    },
]


def _skill_routed_entry(skill_name: str, skill: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": skill_name,
        "slash": f"/{skill_name}",
        "routes_to": {"type": "skill", "id": skill_name},
        "targets": ["claude", "codex", "copilot", "antigravity"],
    }
    capability_id = getattr(skill, "capability_id", None)
    if capability_id is not None:
        entry["capability_id"] = capability_id
    return entry


def _write_command_yaml(cmd_dir: Path, cmd: dict[str, Any]) -> None:
    cmd_dir.mkdir(parents=True, exist_ok=True)
    routes = cmd["routes_to"]
    lines = [
        f'id: "{cmd["id"]}"',
        f'slash: "{cmd["slash"]}"',
        "routes_to:",
        f"  type: {routes['type']}",
    ]
    if routes["type"] == "skill":
        lines.append(f"  id: {routes['id']}")
    else:
        lines.append(f'  command: "{routes["command"]}"')
    if "capability_id" in cmd:
        lines.append(f"capability_id: {cmd['capability_id']}")
    lines.extend(["args: []", "adapter_targets:"])
    for target in cmd.get("targets", []):
        lines.append(f"  - {target}")
    (cmd_dir / "command.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _registry_entry(cmd: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": cmd["id"],
        "slash": cmd["slash"],
        "routes_to": cmd["routes_to"],
        "targets": cmd.get("targets", []),
    }
    if "capability_id" in cmd:
        entry["capability_id"] = cmd["capability_id"]
    return entry


def generate_commands_registry(
    output_dir: str, config: dict[str, Any]
) -> dict[str, Any]:
    """Generate commands registry at .providence/commands/registry.json.

    Writes:
    - .providence/commands/registry.json  index of skill-routed + CLI-routed commands
    - .providence/commands/<id>/command.yaml  individual command definitions

    Args:
        output_dir: Base output directory (workspace root)
        config: Governance configuration dict (unused, kept for API consistency)

    Returns:
        Dict with keys:
            - registry_path: Path to generated registry.json
            - command_count: Number of commands exported
    """
    try:
        from providence_runtime.skills import _REGISTRY

        output_path = Path(output_dir)
        commands_dir = output_path / ".providence" / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)

        commands: list[dict[str, Any]] = []

        # CLI-routed commands take precedence; build an exclusion set first.
        cli_ids = {cmd["id"] for cmd in _CLI_COMMANDS}

        # Skill-routed commands: one per registered skill, unless a CLI route already owns the id.
        commands.extend(
            _skill_routed_entry(skill_name, _REGISTRY[skill_name])
            for skill_name in _REGISTRY
            if skill_name not in cli_ids
        )

        # CLI-routed commands (canonical route for sdd-ask and sdd-organize)
        commands.extend(_CLI_COMMANDS)

        # Write individual command.yaml files
        for cmd in commands:
            _write_command_yaml(commands_dir / cmd["id"], cmd)

        # Write registry.json
        registry = {
            "schema_version": "1.0.0",
            "commands": [_registry_entry(cmd) for cmd in commands],
        }
        registry_path = commands_dir / "registry.json"
        registry_path.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        return {
            "registry_path": registry_path.as_posix(),
            "command_count": len(commands),
        }

    except ImportError:
        return {
            "registry_path": None,
            "command_count": 0,
            "error": "providence_runtime not available",
        }
