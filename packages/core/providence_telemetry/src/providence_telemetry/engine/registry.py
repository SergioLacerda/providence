"""Pattern registry: field-indexed lookup of PatternDef entries for the deduplication engine."""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import Any

from providence_telemetry.types import PatternDef

from .patterns import get_all_patterns


class PatternRegistry:
    """Indexes PatternDef entries by field name for O(fields) pattern lookup."""

    def __init__(self) -> None:
        self._patterns: dict[str, PatternDef] = get_all_patterns()
        self._compiled_regexes: dict[str, re.Pattern[str]] = {}
        self._field_index: dict[str, list[str]] = {}
        self._build_index()

    def _build_index(self) -> None:
        for pid, pattern in self._patterns.items():
            regex = pattern.get("regex")
            if regex is not None:
                self._compiled_regexes[pid] = re.compile(regex, re.IGNORECASE)
            for field in pattern["fields"]:
                self._field_index.setdefault(field, []).append(pid)

    def find_pattern(self, field: str, value: Any) -> str | None:
        """Return the first pattern ID whose definition matches (field, value), or None.

        Patterns are evaluated in insertion order for the given field — the first
        matching pattern wins. Pattern definition order in the pattern modules
        therefore determines precedence when multiple patterns share the same field.
        """
        for pid in self._field_index.get(field, []):
            if self._match(pid, self._patterns[pid], value):
                return pid
        return None

    def _match(self, pattern_id: str, pattern: PatternDef, value: Any) -> bool:
        if (
            isinstance(value, str)
            and pattern_id in self._compiled_regexes
            and self._compiled_regexes[pattern_id].match(value)
        ):
            return True
        return "values" in pattern and value in pattern["values"]

    def get_pattern(self, pattern_id: str) -> PatternDef | None:
        """Return the PatternDef for the given ID, or None if unknown."""
        return self._patterns.get(pattern_id)

    @property
    def patterns(self) -> MappingProxyType[str, PatternDef]:
        """Read-only view of all registered patterns."""
        return MappingProxyType(self._patterns)
