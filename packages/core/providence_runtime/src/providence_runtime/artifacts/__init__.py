"""Typed DTOs for compiled governance artifacts consumed by the runtime.

The runtime executes compiled governance — it never re-parses canonical sources.
Every enforcement decision must be traceable to an artifact loaded here.
"""

from __future__ import annotations

import os

from ._compiled_artifact import ArtifactLoadResult, CompiledArtifact
from ._governance_item import GovernanceItem
from ._item_type import _normalize_item_type, _resolve_item_type

__all__ = [
    "ArtifactLoadResult",
    "CompiledArtifact",
    "GovernanceItem",
    "_normalize_item_type",
    "_resolve_item_type",
    "os",
]
