"""Parsers for mandate.spec and guidelines.dsl governance source files."""

from __future__ import annotations

import re
from collections.abc import Callable

from .models import Guideline, Mandate

_MANDATE_BLOCK = re.compile(r"mandate\s+(\w+)\s*\{([^}]+)\}", re.MULTILINE | re.DOTALL)
_GUIDELINE_BLOCK = re.compile(
    r"guideline\s+(\w+)\s*\{([^}]+)\}", re.MULTILINE | re.DOTALL
)
_MD_MANDATE = re.compile(r"^#{1,3}\s+(M\d{3})[:\s-]+(.+)$", re.MULTILINE)
_MD_GUIDELINE = re.compile(r"^#{1,3}\s+(G\d{3})[:\s-]+(.+)$", re.MULTILINE)
_BULLET_MANDATE = re.compile(r"^-\s+\[(\w+)\]\s+\*\*(.+?)\*\*", re.MULTILINE)


def _extract_field(content: str, field: str) -> str:
    match = re.search(rf'{field}:\s*"([^"]*)"', content)
    return match.group(1) if match else ""


class MandateSpecParser:
    """Parse mandate.spec (or mandate.md fallback) into Mandate objects."""

    def __init__(self, emitter: Callable[[str], None] | None = None) -> None:
        self._emit = emitter or print

    def parse(self, content: str, is_markdown: bool = False) -> list[Mandate]:
        """Parse mandate source content into a list of Mandate objects."""
        if is_markdown:
            return self._parse_markdown(content)
        mandates = self._parse_blocks(content)
        if not mandates:
            mandates = self._parse_bullets(content)
        return mandates

    def _parse_markdown(self, content: str) -> list[Mandate]:
        return [
            Mandate(
                id=mid,
                type="MANDATE",
                title=title.strip(),
                description=title.strip(),
                category="core",
                rationale="",
            )
            for mid, title in _MD_MANDATE.findall(content)
        ]

    def _parse_blocks(self, content: str) -> list[Mandate]:
        mandates = []
        for match in _MANDATE_BLOCK.finditer(content):
            body = match.group(2)
            mandates.append(
                Mandate(
                    id=match.group(1),
                    type=_extract_field(body, "type"),
                    title=_extract_field(body, "title"),
                    description=_extract_field(body, "description"),
                    category=_extract_field(body, "category"),
                    rationale=_extract_field(body, "rationale"),
                )
            )
        return mandates

    def _parse_bullets(self, content: str) -> list[Mandate]:
        return [
            Mandate(
                id=mid,
                type="MANDATE",
                title=title.strip(),
                description=title.strip(),
                category="core",
                rationale="",
            )
            for mid, title in _BULLET_MANDATE.findall(content)
        ]


class GuidelinesDslParser:
    """Parse guidelines.dsl (or guidelines.md fallback) into Guideline objects."""

    def __init__(self, emitter: Callable[[str], None] | None = None) -> None:
        self._emit = emitter or print

    def parse(self, content: str, is_markdown: bool = False) -> list[Guideline]:
        """Parse guideline source content into a list of Guideline objects."""
        if is_markdown:
            return self._parse_markdown(content)
        return self._parse_blocks(content)

    def _parse_markdown(self, content: str) -> list[Guideline]:
        return [
            Guideline(
                id=gid,
                type="GUIDELINE",
                title=title.strip(),
                description=title.strip(),
                category="core",
            )
            for gid, title in _MD_GUIDELINE.findall(content)
        ]

    def _parse_blocks(self, content: str) -> list[Guideline]:
        return [
            Guideline(
                id=match.group(1),
                type=_extract_field(match.group(2), "type"),
                title=_extract_field(match.group(2), "title"),
                description=_extract_field(match.group(2), "description"),
                category=_extract_field(match.group(2), "category"),
            )
            for match in _GUIDELINE_BLOCK.finditer(content)
        ]
