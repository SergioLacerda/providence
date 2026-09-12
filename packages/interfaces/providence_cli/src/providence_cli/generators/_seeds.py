"""Agent seed generators  standalone MD context files per AI platform."""

from pathlib import Path
from typing import Any

from ._seeds_platforms import (
    _generate_antigravity_seed,
    _generate_claude_seed,
    _generate_copilot_seed,
    _generate_cursor_seed,
    _generate_gemini_seed,
    _generate_generic_seed,
)


def generate_agent_seeds(
    output_dir: Path, config: dict[str, Any]
) -> list[tuple[str, Path, str]]:
    """Generate agent seed templates for different AI platforms.

    Args:
        output_dir: Directory to save agent seeds
        config: Governance configuration dictionary

    Returns:
        List of tuples: (agent_name, file_path, status)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    items = config.get("items", [])
    mandatory_rules = [
        i
        for i in items
        if str(i.get("type", "")).upper() == "MANDATE"
        or (i.get("type") == "rule" and i.get("is_immutable"))
    ]
    customizable_items = [i for i in items if not i.get("is_immutable")]

    seeds = [
        ("Cursor IDE", "cursor-agent.md", _generate_cursor_seed),
        ("GitHub Copilot", "copilot-agent.md", _generate_copilot_seed),
        ("Generic AI", "generic-agent.md", _generate_generic_seed),
        ("Claude", "claude-agent.md", _generate_claude_seed),
        ("Gemini", "gemini-agent.md", _generate_gemini_seed),
        ("Antigravity", "antigravity-agent.md", _generate_antigravity_seed),
    ]

    results: list[tuple[str, Path, str]] = []
    for label, filename, generator in seeds:
        path = output_dir / filename
        path.write_text(
            generator(config, mandatory_rules, customizable_items), encoding="utf-8"
        )
        results.append((label, path, "Generated"))

    return results
