#!/usr/bin/env python3
"""
Regenerate source/ directory from governance_items_catalog.json with proper YAML escaping.
"""

import json
import re
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)


def _to_type_key(item_type: str) -> str:
    """Normalize item type to plural directory key."""
    if not item_type:
        return "guidelines"
    if item_type.endswith("s"):
        return item_type
    return f"{item_type}s"


def regenerate_from_catalog(core_path: Path) -> None:
    """Regenerate source/ from catalog JSON"""

    # Load catalog
    catalog_path = core_path.parent / "governance_items_catalog.json"
    if not catalog_path.exists():
        logger.error("%s not found", catalog_path)
        return

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    total_items = catalog.get("total_items", len(catalog.get("all_items", [])))
    logger.info(f"📖 Loaded {total_items} items from catalog")

    # Clear and recreate source/
    source_path = core_path / "source"
    import shutil

    if source_path.exists():
        shutil.rmtree(source_path)
    source_path.mkdir(parents=True, exist_ok=True)

    # Create type directories
    type_dirs: dict[str, Path] = {}
    for item_type in ["mandates", "guidelines", "decisions", "rules", "guardrails"]:
        type_dir = source_path / item_type
        type_dir.mkdir(parents=True, exist_ok=True)
        type_dirs[item_type] = type_dir

    # Regenerate files from all_items
    total = 0
    items_by_type_count: dict[str, int] = {}

    for item in catalog.get("all_items", []):
        item_type = item.get("type", "").lower()
        type_key = _to_type_key(item_type)

        selected_dir = type_dirs.get(type_key)
        if selected_dir is not None:
            write_markdown_file(selected_dir, item)
            total += 1
            items_by_type_count[type_key] = items_by_type_count.get(type_key, 0) + 1

    # Print summary
    for type_key in sorted(items_by_type_count.keys()):
        logger.info(f"   ✓ {type_key}: {items_by_type_count[type_key]} files")

    logger.info(f"   ✓ Total files written: {total}")


def count_type_items(items_data: Any) -> int:
    """Count items in structure (could be list or dict)"""
    if isinstance(items_data, list):
        return len(items_data)
    elif isinstance(items_data, dict):
        total = 0
        for v in items_data.values():
            if isinstance(v, list):
                total += len(v)
            elif isinstance(v, dict):
                total += sum(
                    len(vv) if isinstance(vv, list) else 1 for vv in v.values()
                )
        return total
    return 0


def write_markdown_file(type_dir: Path, item: dict[str, Any]) -> None:
    """Write item as markdown file with proper YAML frontmatter"""

    item_id = item.get("id", "UNKNOWN")
    title = item.get("title", "Untitled")

    # Create frontmatter dict
    frontmatter = {
        "id": item_id,
        "title": title,
        "type": item.get("type", ""),
        "criticality": item.get("criticality", ""),
        "customizable": item.get("customizable", False),
        "optional": item.get("optional", False),
        "category": item.get("category", "general"),
    }

    # Generate YAML with proper escaping
    yaml_str = yaml.dump(
        frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False
    )

    # Create markdown filename
    title_slug = title.lower()
    title_slug = re.sub(r"[^a-z0-9\s-]", "", title_slug)  # Remove special chars
    title_slug = re.sub(r"\s+", "-", title_slug)  # Replace spaces with dashes
    title_slug = title_slug.strip("-")[:50]  # Limit length

    filename = f"{item_id}-{title_slug}.md"

    # Create markdown content
    markdown_content = f"""---
{yaml_str}---

# {item_id}: {title}

## Description

This is a governance item generated from source specifications.

## Details

See the relevant specification file for full information.
"""

    # Write file
    file_path = type_dir / filename
    file_path.write_text(markdown_content, encoding="utf-8")


def main() -> None:
    """Main."""
    from pathlib import Path

    # Determine paths
    current_dir = Path.cwd()
    core_path = current_dir if current_dir.name == "core" else current_dir / "core"

    if not core_path.exists():
        logger.error("%s not found", core_path)
        return

    logger.info("=" * 100)
    logger.info("REGENERATE source/ FROM CATALOG JSON")
    logger.info("=" * 100)

    regenerate_from_catalog(core_path)

    logger.info("=" * 100)
    logger.info("source/ REGENERATED FROM CATALOG")
    logger.info("=" * 100)


if __name__ == "__main__":
    main()
