#!/usr/bin/env python3
"""
Regenerate all markdown files with proper YAML frontmatter using robust parsing.
"""

import re
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)


def extract_items_robust(core_path: Path) -> list[dict[str, Any]]:
    """Extract all items with robust parsing (same as extract_governance_items.py)"""
    items = []

    # Parse mandates
    mandate_spec = core_path / "mandate.spec"
    if mandate_spec.exists():
        mandates = parse_spec_file(mandate_spec.read_text(encoding="utf-8"))
        for m_id, m_data in mandates.items():
            items.append(
                {
                    "id": m_id,
                    "title": m_data["title"],
                    "type": "MANDATE",
                    "criticality": "OBRIGATÓRIO",
                    "customizable": False,
                    "optional": False,
                    "category": m_data.get("category", "general"),
                }
            )

    # Parse guidelines
    guidelines_dsl = core_path / "guidelines.dsl"
    if guidelines_dsl.exists():
        guidelines = parse_spec_file(guidelines_dsl.read_text(encoding="utf-8"))
        for g_id, g_data in guidelines.items():
            items.append(
                {
                    "id": g_id,
                    "title": g_data["title"],
                    "type": "GUIDELINE",
                    "criticality": g_data.get("criticality", "OPCIONAL"),
                    "customizable": g_data.get("customizable", True),
                    "optional": g_data.get("optional", True),
                    "category": g_data.get("category", "general"),
                }
            )

    # Parse markdown files from decisions, rules, guardrails (BEFORE source/)
    for item_type in ["decisions", "rules", "guardrails"]:
        type_dir = core_path / item_type
        if type_dir.exists():
            for md_file in type_dir.glob("*.md"):
                item = parse_markdown_file(md_file)
                if item:
                    items.append(item)

    return items


def parse_spec_file(content: str) -> dict[str, dict[str, Any]]:
    """Parse mandate.spec or guidelines.dsl with brace-counting"""
    items = {}

    # Find ID: {content}
    pattern = r"(\w+):\s*([^{]*?)\s*\{"

    for match in re.finditer(pattern, content):
        item_id = match.group(1).strip()
        title = match.group(2).strip().strip('"')

        # Find matching closing brace
        start_pos = match.end() - 1
        brace_count = 1
        end_pos = start_pos + 1

        while brace_count > 0 and end_pos < len(content):
            if content[end_pos] == "{":
                brace_count += 1
            elif content[end_pos] == "}":
                brace_count -= 1
            end_pos += 1

        properties_str = content[start_pos + 1 : end_pos - 1]

        # Parse properties
        properties: dict[str, Any] = {}
        for prop_match in re.finditer(r'(\w+):\s*"([^"]*)"', properties_str):
            key = prop_match.group(1)
            value = prop_match.group(2)

            # Convert string bools
            if value.lower() == "true":
                properties[key] = True
            elif value.lower() == "false":
                properties[key] = False
            else:
                properties[key] = value

        items[item_id] = {"title": title, **properties}

    return items


def parse_markdown_file(file_path: Path) -> dict[str, Any] | None:
    """Parse YAML frontmatter from markdown file"""
    content = file_path.read_text(encoding="utf-8")

    # Extract YAML frontmatter
    yaml_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not yaml_match:
        return None

    try:
        frontmatter = yaml.safe_load(yaml_match.group(1))
    except yaml.YAMLError:
        return None

    return {
        "id": frontmatter.get("id", ""),
        "title": frontmatter.get("title", ""),
        "type": frontmatter.get("type", ""),
        "criticality": frontmatter.get("criticality", ""),
        "customizable": frontmatter.get("customizable", False),
        "optional": frontmatter.get("optional", False),
        "category": frontmatter.get("category", "general"),
    }


def regenerate_all_markdown(core_path: Path, source_path: Path) -> None:
    """Regenerate all markdown files with proper YAML frontmatter"""
    logger.info("Regenerating all markdown files with proper YAML")

    # Extract all items with robust parsing
    items = extract_items_robust(core_path)
    logger.info(f"   ✓ Extracted {len(items)} items")

    # Organize by type
    by_type: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        type_name = item["type"].lower() + "s"
        if type_name not in by_type:
            by_type[type_name] = []
        by_type[type_name].append(item)

    # Regenerate markdown files
    total_written = 0
    for type_name, type_items in by_type.items():
        type_dir = source_path / type_name
        type_dir.mkdir(parents=True, exist_ok=True)

        for item in type_items:
            # Create filename
            title_slug = item["title"].lower()
            title_slug = re.sub(r"[^a-z0-9]+", "-", title_slug)
            title_slug = title_slug.strip("-")
            filename = f"{item['id']}-{title_slug}.md"

            # Create frontmatter
            frontmatter = {
                "id": item["id"],
                "title": item["title"],
                "type": item["type"],
                "criticality": item["criticality"],
                "customizable": item["customizable"],
                "optional": item["optional"],
                "category": item["category"],
            }

            # Generate markdown
            yaml_str = yaml.dump(
                frontmatter,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

            markdown_content = f"""---
{yaml_str}---

# {item["id"]}: {item["title"]}

## Description

This is a governance item generated from {core_path.name}.

## Details

See the relevant specification file for full information.
"""

            # Write file
            file_path = type_dir / filename
            file_path.write_text(markdown_content, encoding="utf-8")
            total_written += 1

        logger.info(f"   ✓ {type_name}: {len(type_items)} files")

    logger.info(f"   ✓ Total files regenerated: {total_written}")


def main() -> None:
    """Main."""
    from pathlib import Path

    # Determine paths
    current_dir = Path.cwd()
    core_path = current_dir if current_dir.name == "core" else current_dir / "core"

    source_path = core_path / "source"

    if not core_path.exists():
        logger.error("%s not found", core_path)
        return

    logger.info("=" * 100)
    logger.info("REGENERATE ALL MARKDOWN FILES WITH PROPER YAML")
    logger.info("=" * 100)

    # Clear old source/ directory
    import shutil

    if source_path.exists():
        logger.info(f"   🗑️  Clearing {source_path}...")
        shutil.rmtree(source_path)

    source_path.mkdir(parents=True, exist_ok=True)

    # Regenerate all files
    regenerate_all_markdown(core_path, source_path)

    logger.info("=" * 100)
    logger.info("ALL MARKDOWN FILES REGENERATED")
    logger.info("=" * 100)


if __name__ == "__main__":
    main()
