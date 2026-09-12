"""Validation and block-DSL parsing for mandate.spec content."""

from __future__ import annotations

import re
from typing import Any

MANDATE_PATTERN = r"-\s*\[\s*([MP]\d{3})\s*\]\s*\*\*\s*([^*]+?)\s*\*\*"
MANDATE_BLOCK_PATTERN = r"mandate\s+([MP]\d{3})\s*\{([^}]*)\}"


def validate_dsl_syntax(text: str, file_type: str = "dsl") -> list[str]:
    """Validate basic DSL syntax"""
    errors = []

    if file_type == "mandate":
        # Check for lines that look like mandates but are incomplete
        for i, line in enumerate(text.split("\n"), 1):
            line = line.strip()
            if re.match(r"-\s*\[\s*[MP]", line) and not re.search(
                MANDATE_PATTERN, line
            ):
                errors.append(
                    f"Line {i}: Incomplete mandate definition. Expected '- [ID] **Title**'"
                )
    else:
        # Check for balanced braces (for guidelines.dsl)
        if text.count("{") != text.count("}"):
            errors.append(
                f"Unbalanced braces: {text.count('{')} opening, {text.count('}')} closing"
            )

        # Check for balanced quotes
        double_quotes = text.count('"')
        if double_quotes % 2 != 0:
            errors.append(f"Odd number of double quotes: {double_quotes}")

    # Basic sanity: should not be empty
    if not text.strip():
        errors.append("File is empty")

    return errors


def extract_block_field(block_text: str, field: str) -> str:
    """Extract a `field: "value"` entry from a mandate/guideline block body."""
    match = re.search(rf'{field}:\s*"([^"]*)"', block_text)
    return match.group(1) if match else ""


def parse_block_format(mandate_text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse block DSL format: mandate M001 { title: "..." ... }

    Returns (mandates, mandate_ids).
    """
    mandates: list[dict[str, Any]] = []
    mandate_ids: list[str] = []
    for match in re.finditer(
        MANDATE_BLOCK_PATTERN,
        mandate_text,
        re.MULTILINE | re.DOTALL,
    ):
        m_id, block_text = match.groups()
        mandate_ids.append(m_id)
        title = extract_block_field(block_text, "title") or m_id
        metadata = {
            "category": extract_block_field(block_text, "category"),
            "rationale": extract_block_field(block_text, "rationale"),
            "type": extract_block_field(block_text, "type"),
            "description": extract_block_field(block_text, "description"),
        }
        metadata = {key: value for key, value in metadata.items() if value}
        mandates.append({"id": m_id, "title": title, "metadata": metadata})
    return mandates, mandate_ids


def validate_mandate_spec(mandate_text: str) -> dict[str, Any]:
    """Validate mandate.spec structure (Markdown format)."""
    result: dict[str, Any] = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "statistics": {
            "mandate_count": 0,
            "mandate_ids": [],
            "mandates": [],
            "lines": len(mandate_text.split("\n")),
            "bytes": len(mandate_text.encode("utf-8")),
        },
    }

    # Syntax validation
    syntax_errors = validate_dsl_syntax(mandate_text, "mandate")
    if syntax_errors:
        result["valid"] = False
        result["errors"].extend(syntax_errors)

    # Block DSL format: mandate M001 { title: "..." ... }
    mandates, mandate_ids = parse_block_format(mandate_text)

    result["statistics"]["mandates"] = mandates
    result["statistics"]["mandate_count"] = len(mandates)
    result["statistics"]["mandate_ids"] = list(dict.fromkeys(mandate_ids))

    if not mandates:
        result["valid"] = False
        result["errors"].append("No mandates found in specification file")

    if len(mandate_ids) != len(set(mandate_ids)):
        duplicates = [m_id for m_id in set(mandate_ids) if mandate_ids.count(m_id) > 1]
        result["errors"].append(f"Duplicate mandate IDs: {duplicates}")
        result["valid"] = False

    if mandate_ids:
        numeric_ids = sorted(
            [
                int(m_id[1:])
                for m_id in mandate_ids
                if len(m_id) > 1 and m_id[1:].isdigit()
            ]
        )
        if len(numeric_ids) > 1:
            expected_ids = list(
                range(min(numeric_ids), min(numeric_ids) + len(numeric_ids))
            )
            if numeric_ids != expected_ids:
                result["warnings"].append(
                    f"Non-sequential mandate IDs. Found: {mandate_ids}"
                )

    return result
