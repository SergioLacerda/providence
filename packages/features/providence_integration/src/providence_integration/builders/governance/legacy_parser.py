"""Legacy DSL format parsing for governance specifications."""

from __future__ import annotations

import re
from typing import Any

_MALFORMED_TITLE_PATTERN = re.compile(r"^[-*#>|`~]|\s{2,}")


def _valid_title(value: str | None) -> str | None:
    """Return value if it looks like a real title, else None."""
    if not value or not value.strip():
        return None
    if _MALFORMED_TITLE_PATTERN.match(value.strip()):
        return None
    return value.strip() or None


class LegacySpecParser:
    """Parses governance items from legacy `mandate.spec` and `guidelines.dsl` formats."""

    @staticmethod
    def parse_mandates(content: str) -> list[dict[str, Any]]:
        """Parse mandate IDs from legacy mandate.spec formats.

        Supports three formats in order:
        1. Block format: `mandate M001 { ... }`
        2. Compact key-value: `M001: Title`
        3. Bracket fallback: `- [M001] ...`

        Args:
            content: Legacy mandate.spec content

        Returns:
            List of mandate item dicts with id, type, title, status, criticality
        """
        # Block format: `mandate M001 { ... }` — extract title and summaries from body
        block_pattern = re.compile(r"mandate\s+(M\d+)\s*\{([^}]*)\}", re.DOTALL)
        block_matches = block_pattern.findall(content)
        if block_matches:
            items: list[dict[str, Any]] = []
            seen: set[str] = set()
            for mandate_id, body in sorted(block_matches, key=lambda x: x[0]):
                if mandate_id in seen:
                    continue
                seen.add(mandate_id)
                raw_title = LegacySpecParser._extract_block_field(body, "title")
                title = _valid_title(raw_title) or mandate_id
                summary_minimal = _valid_title(
                    LegacySpecParser._extract_block_field(body, "summary_minimal")
                ) or (_valid_title(raw_title))
                summary_runtime = LegacySpecParser._extract_block_field(
                    body, "summary_runtime"
                )
                item: dict[str, Any] = {
                    "id": mandate_id,
                    "type": "MANDATE",
                    "title": title,
                    "status": "active",
                    "criticality": "high",
                    "summary_minimal": summary_minimal,
                    "summary_runtime": summary_runtime,
                }
                items.append(item)
            return items

        # Compact key-value format: `M001: Title`
        kv_matches = re.findall(r"^\s*(M\d+)\s*:\s+(.+)$", content, re.MULTILINE)
        if kv_matches:
            return [
                {
                    "id": mandate_id,
                    "type": "MANDATE",
                    "title": title.strip(),
                    "status": "active",
                    "criticality": "high",
                    "summary_minimal": title.strip(),
                    "summary_runtime": None,
                }
                for mandate_id, title in sorted(
                    {mid: t for mid, t in kv_matches}.items()
                )
            ]

        # Bracket fallback: `- [M001] ...`
        mandate_ids = re.findall(r"\[(M\d+)\]", content)
        unique_ids = sorted(set(mandate_ids))
        return [
            {
                "id": mandate_id,
                "type": "MANDATE",
                "title": "",
                "status": "active",
                "criticality": "high",
                "summary_minimal": None,
                "summary_runtime": None,
            }
            for mandate_id in unique_ids
        ]

    @staticmethod
    def parse_guidelines_blocks(content: str) -> list[dict[str, Any]]:
        """Parse legacy `guideline Gxxx { ... }` blocks preserving title/description.

        Args:
            content: Legacy guidelines.dsl content

        Returns:
            List of guideline item dicts extracted from blocks
        """
        entries: list[dict[str, Any]] = []
        pattern = re.compile(
            r"guideline\s+(G\d+)\s*\{([^}]*)\}", re.IGNORECASE | re.DOTALL
        )
        for match in pattern.finditer(content):
            guideline_id = match.group(1).strip()
            body = match.group(2)
            title = LegacySpecParser._extract_block_field(body, "title") or guideline_id
            description = LegacySpecParser._extract_block_field(body, "description")
            summary_minimal = LegacySpecParser._extract_block_field(
                body, "summary_minimal"
            )
            summary_runtime = LegacySpecParser._extract_block_field(
                body, "summary_runtime"
            )

            item: dict[str, Any] = {
                "id": guideline_id,
                "type": "GUIDELINE",
                "title": title,
                "status": "active",
                "criticality": "medium",
            }
            if description:
                item["description"] = description
            if summary_minimal:
                item["summary_minimal"] = summary_minimal
            if summary_runtime:
                item["summary_runtime"] = summary_runtime
            entries.append(item)

        entries.sort(key=lambda x: x.get("id", ""))
        return entries

    @staticmethod
    def _extract_block_field(block: str, field: str) -> str | None:
        """Extract `field: \"value\"` or `field: value` from a legacy DSL block.

        Args:
            block: Block content (e.g., inside `guideline G001 { ... }`)
            field: Field name to extract (e.g., "title", "description")

        Returns:
            Extracted field value or None if not found
        """
        match = re.search(
            rf"{re.escape(field)}\s*:\s*(?:\"([^\"]*)\"|'([^']*)'|([^\n]+))",
            block,
            re.IGNORECASE,
        )
        if not match:
            return None
        for group in match.groups():
            if group is not None:
                value = group.strip()
                return value or None
        return None
