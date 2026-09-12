#!/usr/bin/env python3
"""
PHASE 1c: Reorganize core/source/
Creates clean source structure with all governance items organized by type.
Metadata (CRITICAL/OPTIONAL/CUSTOMIZABLE) stays in YAML frontmatter, not folder structure.
"""

import json
import re
from pathlib import Path
from shutil import copy2
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class SourceReorganizer:
    """SourceReorganizer."""

    def __init__(self, core_path: str = "core"):
        self.core_path = Path(core_path)
        self.source_path = self.core_path / "source"
        self.source_categories = [
            "mandates",
            "guidelines",
            "decisions",
            "rules",
            "guardrails",
        ]

    def setup_directories(self) -> None:
        """Create clean source directory structure"""
        logger.info("Creating source directory structure")

        # Create source root
        self.source_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for each type
        for category in self.source_categories:
            category_path = self.source_path / category
            category_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"   ✓ {category_path.relative_to(self.core_path)}/")

    def migrate_markdown_items(self) -> None:
        """Migrate existing markdown items (decisions, rules, guardrails) to source/"""
        logger.info("Migrating markdown items to source/")

        for source_type in ["decisions", "rules", "guardrails"]:
            source_dir = self.core_path / source_type
            if not source_dir.exists():
                logger.warning("%s/ not found, skipping", source_type)
                continue

            target_dir = self.source_path / source_type
            md_files = list(source_dir.glob("*.md"))

            if not md_files:
                logger.info(f"   ℹ️  {source_type}/ is empty")
                continue

            for md_file in md_files:
                target_file = target_dir / md_file.name
                copy2(md_file, target_file)
                logger.info(f"   ✓ {md_file.name} → source/{source_type}/")

    def generate_mandates_from_spec(self) -> None:
        """Generate mandate markdown files from mandate.spec"""
        logger.info("Generating mandate files from mandate.spec")

        mandate_file = self.core_path / "mandate.spec"
        if not mandate_file.exists():
            logger.warning("mandate.spec not found, skipping")
            return

        content = mandate_file.read_text(encoding="utf-8")
        mandates_dir = self.source_path / "mandates"

        # Parse mandates
        pattern = r"mandate\s+(\w+)\s*\{"

        for match in re.finditer(pattern, content):
            mandate_id = match.group(1)
            start_pos = match.end()

            # Find matching closing brace
            brace_count = 1
            pos = start_pos
            while pos < len(content) and brace_count > 0:
                if content[pos] == "{":
                    brace_count += 1
                elif content[pos] == "}":
                    brace_count -= 1
                pos += 1

            if brace_count == 0:
                mandate_content = content[start_pos : pos - 1]

                # Extract fields
                title_match = re.search(r'title:\s*"([^"]+)"', mandate_content)
                category_match = re.search(r"category:\s*(\w+)", mandate_content)

                title = title_match.group(1) if title_match else mandate_id
                category = category_match.group(1) if category_match else "general"

                # Create markdown file with YAML frontmatter
                md_filename = f"{mandate_id}-{title.lower().replace(' ', '-')}.md"
                md_path = mandates_dir / md_filename

                markdown_content = f"""---
id: {mandate_id}
title: "{title}"
type: MANDATE
criticality: OBRIGATÓRIO
customizable: false
optional: false
category: {category}
---

# {mandate_id}: {title}

## Description

This is a mandatory governance item generated from mandate.spec.

## Details

See mandate.spec for full specification.
"""

                md_path.write_text(markdown_content, encoding="utf-8")
                logger.info(f"   ✓ {md_filename}")

    def generate_guidelines_from_dsl(self) -> None:
        """Generate guideline markdown files from guidelines.dsl"""
        logger.info("Generating guideline files from guidelines.dsl")

        guidelines_file = self.core_path / "guidelines.dsl"
        if not guidelines_file.exists():
            logger.info("guidelines.dsl not found, skipping")
            return

        content = guidelines_file.read_text(encoding="utf-8")
        guidelines_dir = self.source_path / "guidelines"

        # Parse guidelines
        pattern = r"guideline\s+(\w+)\s*\{"

        count = 0
        for match in re.finditer(pattern, content):
            guideline_id = match.group(1)
            start_pos = match.end()

            # Find matching closing brace
            brace_count = 1
            pos = start_pos
            while pos < len(content) and brace_count > 0:
                if content[pos] == "{":
                    brace_count += 1
                elif content[pos] == "}":
                    brace_count -= 1
                pos += 1

            if brace_count == 0:
                guideline_content = content[start_pos : pos - 1]

                # Extract fields
                title_match = re.search(r'title:\s*"([^"]+)"', guideline_content)
                category_match = re.search(r"category:\s*(\w+)", guideline_content)

                title = title_match.group(1) if title_match else guideline_id
                category = category_match.group(1) if category_match else "general"

                # Create markdown file with YAML frontmatter
                title_clean = title.lower().replace(" ", "-").replace("🛠️", "").strip()
                title_clean = re.sub(
                    r"[^a-z0-9-]", "", title_clean
                )  # Clean up special chars
                md_filename = f"{guideline_id}-{title_clean}.md"
                md_path = guidelines_dir / md_filename

                markdown_content = f"""---
id: {guideline_id}
title: "{title}"
type: GUIDELINE
criticality: OPCIONAL
customizable: true
optional: true
category: {category}
---

# {guideline_id}: {title}

## Description

This is an optional governance guideline generated from guidelines.dsl.

## Details

See guidelines.dsl for full specification.
"""

                md_path.write_text(markdown_content, encoding="utf-8")
                count += 1

                # Only print first 5 to avoid spam
                if count <= 5:
                    logger.info(f"   ✓ {md_filename}")

        # Show summary
        total_guidelines = len(list(re.finditer(pattern, content)))
        if total_guidelines > 5:
            logger.info(f"   ... and {total_guidelines - 5} more guidelines")

    def generate_manifest(self) -> None:
        """Generate manifest showing new structure"""
        logger.info("📊 Generating source/ manifest")

        manifest: dict[str, Any] = {
            "version": "3.0",
            "source_structure": "Flat categorization by type (no CRITICAL/OPTIONAL/CUSTOMIZABLE subfolders)",
            "metadata_location": "YAML frontmatter in each file",
            "categories": {},
        }

        # Count items in each category
        for category in self.source_categories:
            category_path = self.source_path / category
            if category_path.exists():
                md_files = list(category_path.glob("*.md"))
                manifest["categories"][category] = {
                    "path": f"source/{category}",
                    "item_count": len(md_files),
                    "items": [f.stem for f in sorted(md_files)],
                }

        # Save manifest
        manifest_path = self.source_path / "MANIFEST.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        logger.info("Manifest created: source/MANIFEST.json")

    def print_structure(self) -> None:
        """Print the new source structure"""
        logger.info("=" * 100)
        logger.info("NEW SOURCE STRUCTURE")
        logger.info("=" * 100)
        logger.info(f"Path: {self.source_path}")

        for category in self.source_categories:
            category_path = self.source_path / category
            if category_path.exists():
                md_files = sorted(list(category_path.glob("*.md")))
                logger.info(f"📁 source/{category}/ ({len(md_files)} items)")

                # Show first 3 items
                for md_file in md_files[:3]:
                    logger.info(f"   • {md_file.name}")

                if len(md_files) > 3:
                    logger.info(f"   ... and {len(md_files) - 3} more")

    def run(self) -> None:
        """Execute full reorganization"""
        logger.info("=" * 100)
        logger.info("🔧 PHASE 1c: REORGANIZE core/source/")
        logger.info("=" * 100)

        self.setup_directories()
        self.migrate_markdown_items()
        self.generate_mandates_from_spec()
        self.generate_guidelines_from_dsl()
        self.generate_manifest()
        self.print_structure()

        logger.info("=" * 100)
        logger.info("PHASE 1c COMPLETE")
        logger.info("=" * 100)
        logger.info("Next steps:")
        logger.info("1. Review source/ structure")
        logger.info("2. Verify compiler still works: python core/pipeline_builder.py")
        logger.info("3. Proceed to PHASE 1c-test")


if __name__ == "__main__":
    from pathlib import Path

    # Determine correct path
    current_dir = Path.cwd()
    core_path = current_dir if current_dir.name == "core" else current_dir / "core"

    reorganizer = SourceReorganizer(str(core_path))
    reorganizer.run()
