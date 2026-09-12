"""IDE-specific governance instruction file generators."""

from pathlib import Path
from typing import Any

from ._instruction_sections import (
    build_instruction_targets,
    guard_repo_root_mutation,
    write_instruction_files,
)
from ._shared import _fingerprint_prefix


def generate_agent_instruction_files(
    output_dir: Path, config: dict[str, Any]
) -> list[tuple[str, Path]]:
    """Generate governance instruction files for supported IDEs and agents."""
    # Safeguard: Never mutate the project root during tests
    guard_repo_root_mutation(output_dir)

    items = config.get("items", [])
    item_count = len(items)

    # G4 Guard: Never generate empty instruction files
    if item_count == 0:
        return []

    core_header = _fingerprint_prefix(config, "core_fingerprint", 16)
    outputs = build_instruction_targets(output_dir, core_header, item_count)

    fingerprint = _fingerprint_prefix(config, "core_fingerprint", 16)
    mandate_ids = [
        str(item.get("id", ""))
        for item in items
        if str(item.get("type", "")).upper() == "MANDATE" and item.get("id")
    ]

    return write_instruction_files(outputs, fingerprint, mandate_ids)


def generate_copilot_instructions(output_dir: Path, config: dict[str, Any]) -> Path:
    """Generate .github/copilot-instructions.md with real governance content.

    Derives content from governance-core.json items: MANDATEs, GUIDELINEs,
    and DECISION items with their descriptions.

    Args:
        output_dir: Workspace root (file goes to output_dir/.github/).
        config: Governance config dict loaded from governance-core.json.

    Returns:
        Path to the written copilot-instructions.md file.
    """
    return generate_agent_instruction_files(output_dir, config)[0][1]
