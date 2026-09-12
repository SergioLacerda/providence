"""Primary-path parsing of governed .providence artifacts (mandates.md, guidelines.dsl).

Used by SelectorCompiler when compiled .providence artifacts are present.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ._selector_models import _parse_guideline_dsl_block, _parse_section_body


def _load_metadata(metadata_path: Path) -> dict[str, str]:
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    mandates = payload.get("mandates")
    if not isinstance(mandates, dict):
        raise ValueError(".providence/metadata.json mandates must be a mapping.")
    return {str(key): str(value) for key, value in mandates.items()}


def _load_guidelines_metadata(guidelines_path: Path) -> dict[str, str]:
    """Parse guidelines.dsl and return {id: title} mapping."""
    content = guidelines_path.read_text(encoding="utf-8")
    result: dict[str, str] = {}
    for match in re.finditer(
        r"guideline\s+(\w+)\s*\{([^}]+)\}", content, re.MULTILINE | re.DOTALL
    ):
        gid = match.group(1)
        body = match.group(2)
        title_match = re.search(r'title:\s*"([^"]*)"', body)
        if title_match:
            result[gid] = title_match.group(1)
    return result


def _parse_mandate_sections(mandates_path: Path) -> dict[str, dict[str, object]]:
    content = mandates_path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^## (M\d+): (.+)$", content, flags=re.MULTILINE))
    sections: dict[str, dict[str, object]] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        section_body = content[start:end].strip()
        item_id = match.group(1)
        if item_id in sections:
            raise ValueError(f"Duplicate mandate section for {item_id}")
        sections[item_id] = _parse_section_body(section_body)
    return sections


def _parse_guideline_dsl_sections(
    guidelines_path: Path,
) -> dict[str, dict[str, object]]:
    """Parse all guideline blocks from guidelines.dsl."""
    content = guidelines_path.read_text(encoding="utf-8")
    sections: dict[str, dict[str, object]] = {}
    for match in re.finditer(
        r"guideline\s+(\w+)\s*\{([^}]+)\}", content, re.MULTILINE | re.DOTALL
    ):
        gid = match.group(1)
        sections[gid] = _parse_guideline_dsl_block(match.group(2))
    return sections
