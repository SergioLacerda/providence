"""Registry loaders for prompt command generation (slash aliases, command entries)."""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Any


def _load_slash_aliases(output_dir: Path) -> list[tuple[str, str]]:
    """Load slash aliases from canonical command registry with safe fallback."""
    registry_path = output_dir / ".providence" / "commands" / "registry.json"
    aliases: list[tuple[str, str]] = []
    try:
        data = _json.loads(registry_path.read_text(encoding="utf-8"))
        commands = data.get("commands", [])
        if isinstance(commands, list):
            for cmd in commands:
                if not isinstance(cmd, dict):
                    continue
                slash = str(cmd.get("slash", "")).strip()
                cmd_id = str(cmd.get("id", "")).strip()
                if slash and cmd_id:
                    aliases.append((slash, cmd_id))
    except Exception:
        aliases = []

    if not aliases:
        aliases = [
            ("/sdd-diagnose", "sdd-diagnose"),
            ("/sdd-validate-governance", "sdd-validate-governance"),
            ("/sdd-stabilize", "sdd-stabilize"),
            ("/sdd-compress-context", "sdd-compress-context"),
            ("/sdd-review-architecture", "sdd-review-architecture"),
            ("/sdd-correct", "sdd-correct"),
            ("/sdd-converge", "sdd-converge"),
            ("/sdd-ask", "sdd-ask"),
            ("/sdd-organize", "sdd-organize"),
        ]

    alias_map = {slash: cmd_id for slash, cmd_id in aliases}
    return [(slash, cmd_id) for slash, cmd_id in alias_map.items()]


def _load_command_entries(output_dir: Path) -> list[dict[str, Any]]:
    """Load full command entries from canonical registry with safe fallback."""
    registry_path = output_dir / ".providence" / "commands" / "registry.json"
    try:
        data = _json.loads(registry_path.read_text(encoding="utf-8"))
        commands = data.get("commands", [])
        if isinstance(commands, list):
            out: list[dict[str, Any]] = []
            for cmd in commands:
                if not isinstance(cmd, dict):
                    continue
                slash = str(cmd.get("slash", "")).strip()
                cmd_id = str(cmd.get("id", "")).strip()
                routes = cmd.get("routes_to", {})
                if slash and cmd_id and isinstance(routes, dict):
                    out.append(cmd)
            if out:
                return out
    except (OSError, ValueError):
        return _default_command_entries()

    # Fallback for early bootstrap without registry available.
    return _default_command_entries()


def _default_command_entries() -> list[dict[str, Any]]:
    """Return minimal command set used before registry generation."""
    return [
        {
            "id": "sdd-ask",
            "slash": "/sdd-ask",
            "routes_to": {"type": "cli", "command": "providence ask"},
        },
        {
            "id": "sdd-organize",
            "slash": "/sdd-organize",
            "routes_to": {"type": "cli", "command": "providence organize"},
        },
    ]
