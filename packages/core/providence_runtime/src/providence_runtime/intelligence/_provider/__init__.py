"""IntelligenceProvider Protocol and the always-available local provider.

Reference: .providence/runtime analytics design §Phase 5
"""

from __future__ import annotations

from ._constants import (
    _BUDGET_MAX_BYTES,
    _BUDGET_MIN_BYTES,
    _BYTES_PER_QUERY_CHAR,
    _COMPLEXITY_HIGH,
    _COMPLEXITY_HIGH_THRESHOLD,
    _COMPLEXITY_LOW,
    _COMPLEXITY_LOW_THRESHOLD,
    _COMPLEXITY_MED,
    _LOCAL_CONFIDENCE,
    _PATH_FROM_BUDGET,
    _PATH_HIGH_COMPLEXITY,
    _PATH_SUGGESTION,
    _TASK_CLASS_KEYWORDS,
)
from ._local import LocalIntelligenceProvider
from ._protocol import IntelligenceProvider

__all__ = [
    "_BUDGET_MAX_BYTES",
    "_BUDGET_MIN_BYTES",
    "_BYTES_PER_QUERY_CHAR",
    "_COMPLEXITY_HIGH",
    "_COMPLEXITY_HIGH_THRESHOLD",
    "_COMPLEXITY_LOW",
    "_COMPLEXITY_LOW_THRESHOLD",
    "_COMPLEXITY_MED",
    "_LOCAL_CONFIDENCE",
    "_PATH_FROM_BUDGET",
    "_PATH_HIGH_COMPLEXITY",
    "_PATH_SUGGESTION",
    "_TASK_CLASS_KEYWORDS",
    "IntelligenceProvider",
    "LocalIntelligenceProvider",
]
