#!/usr/bin/env python3
"""
Fix YAML frontmatter in markdown files with invalid escaping.
Regenerates all markdown files with proper YAML serialization.
"""

import re
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)


def read_dsl_file(file_path: Path) -> dict[str, dict[str, Any]]:
    """Read DSL file and parse entries"""
    entries: dict[str, dict[str, Any]] = {}

    if not file_path.exists():
        return entries

    content = file_path.read_text(encoding="utf-8")

    # Pattern: id:Title { properties }
    pattern = r"(\w+):([^{]+)\{([^}]+)\}"

    for match in re.finditer(pattern, content):
        item_id = match.group(1).strip()
        title = match.group(2).strip()
        properties_str = match.group(3).strip()

        # Parse properties
        properties: dict[str, Any] = {}
        for prop_match in re.finditer(r'(\w+):\s*"([^"]*)"', properties_str):
            prop_key = prop_match.group(1).lower()
            prop_value = prop_match.group(2)
            properties[prop_key] = prop_value

        entries[item_id] = {"title": title, "properties": properties}

    return entries


def regenerate_guideline_files(source_path: Path) -> None:
    """Regenerate all guideline markdown files with proper YAML"""
    logger.info("🔧 Regenerating guideline markdown files with proper YAML")

    guidelines_dir = source_path / "guidelines"
    if not guidelines_dir.exists():
        logger.warning("source/guidelines/ not found")
        return

    # Read from guidelines.dsl to get titles
    dsl_path = source_path.parent / "guidelines.dsl"
    dsl_entries = read_dsl_file(dsl_path)

    logger.info(f"   ✓ Loaded {len(dsl_entries)} entries from guidelines.dsl")

    # Regenerate each markdown file
    count = 0
    for md_file in sorted(guidelines_dir.glob("*.md")):
        # Extract ID from filename: G01--name.md → G01
        id_match = re.match(r"^([A-Z]\d+)", md_file.stem)
        if not id_match:
            continue

        item_id = id_match.group(1)

        if item_id not in dsl_entries:
            continue

        entry = dsl_entries[item_id]
        title = entry["title"]
        properties = entry["properties"]

        # Create frontmatter dict
        frontmatter = {
            "id": item_id,
            "title": title,
            "type": "GUIDELINE",
            "criticality": properties.get("criticality", "OPCIONAL"),
            "customizable": properties.get("customizable", "true").lower() == "true",
            "optional": properties.get("optional", "true").lower() == "true",
            "category": properties.get("category", "general"),
        }

        # Create markdown content
        yaml_frontmatter = yaml.dump(
            frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False
        )
        markdown_content = f"""---
{yaml_frontmatter}---

# {item_id}: {title}

## Description

This is an optional governance guideline generated from guidelines.dsl.

## Details

See guidelines.dsl for full specification.
"""

        # Write file
        md_file.write_text(markdown_content, encoding="utf-8")
        count += 1

        if count % 10 == 0:
            logger.info(f"   ✓ Regenerated {count} files...")

    logger.info(f"   ✓ Regenerated {count} guideline files with proper YAML")


def regenerate_mandate_files(source_path: Path) -> None:
    """Regenerate mandate markdown files with proper YAML"""
    logger.info("🔧 Regenerating mandate markdown files with proper YAML")

    mandates_dir = source_path / "mandates"
    if not mandates_dir.exists():
        logger.warning("source/mandates/ not found")
        return

    # Read from mandate.spec
    spec_path = source_path.parent / "mandate.spec"

    if not spec_path.exists():
        logger.warning("mandate.spec not found")
        return

    # Parse mandate.spec
    mandates: dict[str, dict[str, Any]] = {}
    content = spec_path.read_text(encoding="utf-8")

    pattern = r"(\w+):([^{]+)\{([^}]+)\}"
    for match in re.finditer(pattern, content):
        mandate_id = match.group(1).strip()
        title = match.group(2).strip()
        properties_str = match.group(3).strip()

        properties: dict[str, Any] = {}
        for prop_match in re.finditer(r'(\w+):\s*"([^"]*)"', properties_str):
            prop_key = prop_match.group(1).lower()
            prop_value = prop_match.group(2)
            properties[prop_key] = prop_value

        mandates[mandate_id] = {"title": title, "properties": properties}

    logger.info(f"   ✓ Loaded {len(mandates)} mandates from mandate.spec")

    # Regenerate each mandate file
    for md_file in sorted(mandates_dir.glob("*.md")):
        id_match = re.match(r"^([A-Z]\d+)", md_file.stem)
        if not id_match:
            continue

        mandate_id = id_match.group(1)

        if mandate_id not in mandates:
            continue

        mandate = mandates[mandate_id]
        title = mandate["title"]
        properties = mandate["properties"]

        frontmatter = {
            "id": mandate_id,
            "title": title,
            "type": "MANDATE",
            "criticality": "OBRIGATÓRIO",
            "customizable": False,
            "optional": False,
            "category": properties.get("category", "general"),
        }

        yaml_frontmatter = yaml.dump(
            frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False
        )
        markdown_content = f"""---
{yaml_frontmatter}---

# {mandate_id}: {title}

## Description

This is a mandatory governance item generated from mandate.spec.

## Details

See mandate.spec for full specification.
"""

        md_file.write_text(markdown_content, encoding="utf-8")

    logger.info(f"   ✓ Regenerated {len(mandates)} mandate files with proper YAML")


def main() -> None:
    """Main."""
    from pathlib import Path

    # Determine correct path
    current_dir = Path.cwd()
    core_path = current_dir if current_dir.name == "core" else current_dir / "core"

    source_path = core_path / "source"

    if not source_path.exists():
        logger.error("source/ directory not found")
        return

    logger.info("=" * 100)
    logger.info("🔧 FIX YAML FRONTMATTER IN MARKDOWN FILES")
    logger.info("=" * 100)

    regenerate_guideline_files(source_path)
    regenerate_mandate_files(source_path)

    logger.info("=" * 100)
    logger.info("YAML FRONTMATTER FIXED")
    logger.info("=" * 100)


if __name__ == "__main__":
    main()
