"""DSL parsers for mandate.spec and guidelines.dsl source formats."""

from __future__ import annotations

import re
from typing import Any


def parse_mandate_spec_text(text: str) -> tuple[int, list[dict[str, Any]]]:
    """Parse mandate.spec DSL format"""
    mandates = []

    # Pattern: mandate M001 { ... }
    mandate_pattern = r"mandate\s+(M\d+)\s*\{([^}]*)\}"

    for match in re.finditer(mandate_pattern, text, re.DOTALL):
        mandate_id = match.group(1)
        mandate_body = match.group(2)

        # Extract fields
        type_match = re.search(r"type:\s*(\w+)", mandate_body)
        title_match = re.search(r'title:\s*"([^"]*)"', mandate_body)
        description_match = re.search(
            r'description:\s*"([^"]*)"', mandate_body, re.DOTALL
        )
        criticality_match = re.search(r"criticality:\s*(\w+)", mandate_body)

        mandate = {
            "id": mandate_id,
            "id_num": int(mandate_id[1:]),  # M001  1
            "type": type_match.group(1) if type_match else "HARD",
            "title": title_match.group(1) if title_match else "Unknown",
            "description": (
                description_match.group(1).replace("\n", " ").strip()[:500]
                if description_match
                else ""
            ),
            "criticality": (
                criticality_match.group(1) if criticality_match else "MANDATORY"
            ),
        }
        mandates.append(mandate)

    return len(mandates), mandates


def parse_guidelines_dsl_text(text: str) -> tuple[int, list[dict[str, Any]]]:
    """Parse guidelines.dsl DSL format"""
    guidelines = []

    # Pattern: guideline G001 { ... }
    guideline_pattern = r"guideline\s+(G\d+)\s*\{([^}]*)\}"

    guide_num = 0
    for match in re.finditer(guideline_pattern, text, re.DOTALL):
        guide_id = match.group(1)
        guide_body = match.group(2)

        # Extract fields
        type_match = re.search(r"type:\s*(\w+)", guide_body)
        title_match = re.search(r'title:\s*"([^"]*)"', guide_body)
        description_match = re.search(
            r'description:\s*"([^"]*)"', guide_body, re.DOTALL
        )
        category_match = re.search(r"category:\s*(\w+)", guide_body)

        # Extract number from guide_id (G01  1)
        num_match = re.search(r"G(\d+)", guide_id)
        guide_num = int(num_match.group(1)) if num_match else guide_num + 1

        guideline = {
            "id": guide_id,
            "id_num": guide_num,
            "type": type_match.group(1) if type_match else "SOFT",
            "title": title_match.group(1) if title_match else "Unknown",
            "description": (
                description_match.group(1).replace("\n", " ").strip()[:300]
                if description_match
                else ""
            ),
            "category": (
                category_match.group(1).lower() if category_match else "general"
            ),
        }
        guidelines.append(guideline)

    return len(guidelines), guidelines
