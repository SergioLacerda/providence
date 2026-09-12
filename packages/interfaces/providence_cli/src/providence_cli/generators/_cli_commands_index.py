"""CLI commands discovery index generator."""

import json
from pathlib import Path
from typing import Any, cast


def _timestamp_iso8601() -> str:
    """Generate ISO 8601 timestamp for index generation."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def generate_cli_commands_index(
    output_dir: str, config: dict[str, Any]
) -> dict[str, Any]:
    """Generate CLI commands discovery index.

    Writes:
    - .providence/indices/cli.commands.json  searchable command metadata

    Args:
        output_dir: Base output directory (workspace root)
        config: Governance configuration dict

    Returns:
        Dict with keys:
            - index_path: Path to generated cli.commands.json
            - command_count: Number of commands indexed
    """
    try:
        output_path = Path(output_dir)
        indices_dir = output_path / ".providence" / "indices"
        indices_dir.mkdir(parents=True, exist_ok=True)

        commands = [
            {
                "name": "providence ask",
                "group": "governance",
                "purpose": "Query governance context",
                "flags": ["--dossier", "--skill", "--budget"],
                "governed_by": ["M010"],
                "requires_handshake": True,
            },
            {
                "name": "providence ask --full",
                "group": "governance",
                "purpose": "Query governance with full context and compression",
                "flags": [],
                "governed_by": ["M010"],
                "requires_handshake": True,
            },
            {
                "name": "providence governance compile",
                "group": "governance",
                "purpose": "Compile governance sources to msgpack",
                "flags": [],
                "governed_by": ["M005", "M008"],
                "requires_handshake": False,
            },
            {
                "name": "providence governance generate",
                "group": "governance",
                "purpose": "Generate agent seeds and skills registry",
                "flags": ["--output-dir", "--path"],
                "governed_by": ["M005"],
                "requires_handshake": False,
            },
            {
                "name": "providence governance validate",
                "group": "governance",
                "purpose": "Validate governance integrity",
                "flags": [],
                "governed_by": ["M005"],
                "requires_handshake": False,
            },
            {
                "name": "sdd skill",
                "group": "skills",
                "purpose": "Execute or inspect a skill",
                "flags": ["--execute", "--list"],
                "governed_by": ["M020"],
                "requires_handshake": True,
            },
            {
                "name": "sdd metrics show",
                "group": "metrics",
                "purpose": "Display token economy metrics",
                "flags": ["--format"],
                "governed_by": ["M005"],
                "requires_handshake": False,
            },
            {
                "name": "providence runtime status",
                "group": "runtime",
                "purpose": "Check runtime health and configuration",
                "flags": [],
                "governed_by": [],
                "requires_handshake": False,
            },
        ]

        commands_index = {
            "schema_version": "1.0.0",
            "index_type": "cli_commands",
            "generated_at": _timestamp_iso8601(),
            "total_commands": len(commands),
            "commands": sorted(
                commands,
                key=lambda c: cast(str, c["name"]),
            ),
        }

        index_path = indices_dir / "cli.commands.json"
        index_path.write_text(
            json.dumps(commands_index, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        return {
            "index_path": index_path.as_posix(),
            "command_count": len(commands),
            "commands": [cmd["name"] for cmd in commands],
        }

    except Exception as e:
        return {
            "index_path": None,
            "command_count": 0,
            "commands": [],
            "error": str(e),
        }
