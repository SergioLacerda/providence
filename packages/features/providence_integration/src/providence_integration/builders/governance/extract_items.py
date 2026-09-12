#!/usr/bin/env python3
"""
PHASE 1a: Extract and List All Governance Items
Reads mandate.spec, guidelines.dsl, decisions/*.md, rules/*.md, guardrails/*.md
Outputs JSON with all items tagged with [CRITICAL/OPTIONAL/CUSTOMIZABLE]
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)


class GovernanceItemExtractor:
    """GovernanceItemExtractor."""

    def __init__(self, core_path: str | Path = ".") -> None:
        self.core_path = Path(core_path)
        self.items: list[dict[str, Any]] = []

    def extract_all(self) -> list[dict[str, Any]]:
        """Extract all items from all sources"""
        logger.info("PHASE 1a: Extracting all governance items")

        # Extract mandates from mandate.spec
        logger.info("Reading mandate.spec")
        mandates = self._extract_mandates()
        logger.info(f"   → Found {len(mandates)} mandates")
        self.items.extend(mandates)

        # Extract guidelines from guidelines.dsl
        logger.info("Reading guidelines.dsl")
        guidelines = self._extract_guidelines()
        logger.info(f"   → Found {len(guidelines)} guidelines")
        self.items.extend(guidelines)

        # Extract decisions from decisions/*.md
        logger.info("Reading decisions/*.md")
        decisions = self._extract_markdown_items("decisions", "DECISION")
        logger.info(f"   → Found {len(decisions)} decisions")
        self.items.extend(decisions)

        # Extract rules from rules/*.md
        logger.info("Reading rules/*.md")
        rules = self._extract_markdown_items("rules", "RULE")
        logger.info(f"   → Found {len(rules)} rules")
        self.items.extend(rules)

        # Extract guardrails from guardrails/*.md
        logger.info("Reading guardrails/*.md")
        guardrails = self._extract_markdown_items("guardrails", "GUARDRAIL")
        logger.info(f"   → Found {len(guardrails)} guardrails")
        self.items.extend(guardrails)

        logger.info(f"✅ Total items extracted: {len(self.items)}")

        return self.items

    def _extract_mandates(self) -> list[dict[str, Any]]:
        """Extract mandates from mandate.spec"""
        mandate_file = self.core_path / "mandate.spec"
        if not mandate_file.exists():
            return []

        content = mandate_file.read_text(encoding="utf-8")
        mandates = []

        # Parse: mandate M001 { ... } with proper bracket matching
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

                # Extract title and other fields
                title_match = re.search(r'title:\s*"([^"]+)"', mandate_content)
                category_match = re.search(r"category:\s*(\w+)", mandate_content)

                title = title_match.group(1) if title_match else mandate_id
                category = category_match.group(1) if category_match else "general"

                mandate = {
                    "id": mandate_id,
                    "title": title,
                    "type": "MANDATE",
                    "criticality": "OBRIGATÓRIO",  # Mandates are always mandatory
                    "customizable": False,  # Mandates cannot be customized
                    "optional": False,
                    "category": category,
                    "source_file": "mandate.spec",
                    "tag": "[CRITICAL]",  # For user display
                }
                mandates.append(mandate)

        return mandates

    def _extract_guidelines(self) -> list[dict[str, Any]]:
        """Extract guidelines from guidelines.dsl"""
        guidelines_file = self.core_path / "guidelines.dsl"
        if not guidelines_file.exists():
            return []

        content = guidelines_file.read_text(encoding="utf-8")
        guidelines = []

        # Parse: guideline G01 { ... } with proper bracket matching
        pattern = r"guideline\s+(\w+)\s*\{"

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

                # Extract title and other fields
                title_match = re.search(r'title:\s*"([^"]+)"', guideline_content)
                category_match = re.search(r"category:\s*(\w+)", guideline_content)
                type_match = re.search(r"type:\s*(\w+)", guideline_content)

                title = title_match.group(1) if title_match else guideline_id
                category = category_match.group(1) if category_match else "general"
                type_match.group(1) if type_match else "SOFT"

                # Guidelines are typically customizable by default
                guideline = {
                    "id": guideline_id,
                    "title": title,
                    "type": "GUIDELINE",
                    "criticality": "OPCIONAL",  # Guidelines are optional by default
                    "customizable": True,  # Guidelines can be customized
                    "optional": True,
                    "category": category,
                    "source_file": "guidelines.dsl",
                    "tag": "[OPTIONAL/CUSTOMIZABLE]",  # Can be CORE or CLIENT
                }
                guidelines.append(guideline)

        return guidelines

    def _extract_markdown_items(
        self, subdir: str, item_type: str
    ) -> list[dict[str, Any]]:
        """Extract items from markdown files with YAML frontmatter"""
        items_dir = self.core_path / subdir
        if not items_dir.exists():
            return []

        items = []

        for md_file in sorted(items_dir.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")

            # Extract YAML frontmatter
            yaml_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if not yaml_match:
                continue

            try:
                frontmatter = yaml.safe_load(yaml_match.group(1))
            except yaml.YAMLError:
                continue

            item_id = frontmatter.get("id", md_file.stem)
            title = frontmatter.get("title", item_id)
            criticality = frontmatter.get("criticality", "OPCIONAL")
            customizable = frontmatter.get("customizable", False)
            optional = frontmatter.get("optional", True)
            category = frontmatter.get("category", "general")

            # Determine tag based on criticality and customizable
            if criticality == "OBRIGATÓRIO":
                tag = "[CRITICAL]"
            elif customizable:
                tag = "[CUSTOMIZABLE]"
            else:
                tag = "[OPTIONAL]"

            item = {
                "id": item_id,
                "title": title,
                "type": item_type,
                "criticality": criticality,
                "customizable": customizable,
                "optional": optional,
                "category": category,
                "source_file": str(md_file.relative_to(self.core_path)),
                "tag": tag,
            }
            items.append(item)

        return items

    def export_json(
        self, output_file: str = "governance_items_catalog.json"
    ) -> dict[str, Any]:
        """Export extracted items to JSON"""
        output_path = Path(output_file)

        # Group by type for organization
        items_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in self.items:
            item_type = item["type"]
            items_by_type[item_type].append(item)

        # Create output structure
        output = {
            "version": "3.0",
            "generated_at": datetime.now().isoformat(),
            "total_items": len(self.items),
            "summary": {
                "MANDATE": len(items_by_type.get("MANDATE", [])),
                "GUIDELINE": len(items_by_type.get("GUIDELINE", [])),
                "DECISION": len(items_by_type.get("DECISION", [])),
                "RULE": len(items_by_type.get("RULE", [])),
                "GUARDRAIL": len(items_by_type.get("GUARDRAIL", [])),
            },
            "items_by_type": items_by_type,
            "all_items": self.items,
        }

        output_path.write_text(
            json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(f"✅ Exported to: {output_path}")
        return output

    def print_summary(self) -> None:
        """Print human-readable summary"""
        items_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in self.items:
            item_type = item["type"]
            items_by_type[item_type].append(item)

        logger.info("=" * 100)
        logger.info("GOVERNANCE ITEMS CATALOG - PHASE 1a")
        logger.info("=" * 100)

        for item_type in ["MANDATE", "GUIDELINE", "DECISION", "RULE", "GUARDRAIL"]:
            if item_type in items_by_type:
                items = items_by_type[item_type]
                logger.info(f"📋 {item_type} ({len(items)} items)")
                logger.info("-" * 100)

                # Group by tag
                by_tag: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for item in items:
                    tag = item["tag"]
                    by_tag[tag].append(item)

                for tag in sorted(by_tag.keys()):
                    tag_items = by_tag[tag]
                    logger.info(f"  {tag} ({len(tag_items)})")

                    for item in tag_items[:3]:  # Show first 3 of each tag
                        logger.info(f"    • {item['id']}: {item['title'][:70]}")

                    if len(tag_items) > 3:
                        logger.info(f"    ... and {len(tag_items) - 3} more")


if __name__ == "__main__":
    # Determine the correct path to core
    # If running from core/ dir, use parent dir
    # If running from root, use core/
    current_dir = Path.cwd()
    core_path = current_dir if current_dir.name == "core" else current_dir / "core"

    logger.info(f"📍 Using core path: {core_path}")

    extractor = GovernanceItemExtractor(core_path)
    extractor.extract_all()
    extractor.print_summary()

    # Export to root governance_items_catalog.json
    catalog_path = current_dir / "governance_items_catalog.json"
    extractor.export_json(str(catalog_path))

    # Print selection prompt
    logger.info("=" * 100)
    logger.info("PHASE 1b: USER SELECTION (NEXT STEP)")
    logger.info("=" * 100)
    logger.info("📌 Items marked [CRITICAL] → MUST STAY IN CORE (no user choice)")
    logger.info(
        "📌 Items marked [OPTIONAL/CUSTOMIZABLE] → USER CHOOSES: CORE or CLIENT"
    )
    logger.info("Next: governance_items_catalog.json ready for PHASE 1b user selection")
