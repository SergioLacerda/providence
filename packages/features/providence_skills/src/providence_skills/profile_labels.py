"""Resolve legacy sdd-* skill/route IDs to Providence-branded display labels.

Display-only: registry IDs are never renamed. See ADR-018.
"""

from __future__ import annotations

_LEGACY_PREFIX = "sdd-"
_PROVIDENCE_PREFIX = "providence-"


def resolve_profile_label(value: str) -> str:
    """Return the Providence-branded display label for a profile/skill id.

    Any string starting with ``sdd-`` becomes ``providence-<suffix>``.
    Everything else (``default``, workspace types like ``client``/``master``,
    already-resolved ``providence-*`` labels, empty strings) passes through
    unchanged.
    """
    if value.startswith(_LEGACY_PREFIX):
        return _PROVIDENCE_PREFIX + value[len(_LEGACY_PREFIX) :]
    return value
