"""Heuristic constants for LocalIntelligenceProvider."""

from __future__ import annotations

__all__ = [
    "_TASK_CLASS_KEYWORDS",
    "_COMPLEXITY_LOW_THRESHOLD",
    "_COMPLEXITY_HIGH_THRESHOLD",
    "_COMPLEXITY_LOW",
    "_COMPLEXITY_MED",
    "_COMPLEXITY_HIGH",
    "_PATH_SUGGESTION",
    "_PATH_HIGH_COMPLEXITY",
    "_BYTES_PER_QUERY_CHAR",
    "_BUDGET_MIN_BYTES",
    "_BUDGET_MAX_BYTES",
    "_LOCAL_CONFIDENCE",
    "_PATH_FROM_BUDGET",
]

# Task class keyword table — first match wins (order matters).
_TASK_CLASS_KEYWORDS: dict[str, list[str]] = {
    "bug-fix": ["fix", "bug", "error", "crash", "fail", "broken", "issue", "wrong"],
    "feature": ["add", "implement", "create", "new", "feature", "build", "introduce"],
    "refactor": [
        "refactor",
        "restructure",
        "rename",
        "move",
        "clean",
        "reorganize",
        "extract",
    ],
    "test": ["test", "spec", "coverage", "assert", "mock", "fixture"],
    "docs": ["doc", "readme", "explain", "comment", "document", "describe"],
}

# Complexity bands based on query character length.
_COMPLEXITY_LOW_THRESHOLD: int = 50  # < 50 chars  → low   (0.2)
_COMPLEXITY_HIGH_THRESHOLD: int = 200  # > 200 chars → high  (0.8)
_COMPLEXITY_LOW: float = 0.2
_COMPLEXITY_MED: float = 0.5
_COMPLEXITY_HIGH: float = 0.8

# PATH suggestion table: (task_class, complexity_band) → path_id.
_PATH_SUGGESTION: dict[tuple[str, str], str] = {
    ("bug-fix", "low"): "A",
    ("bug-fix", "medium"): "A",
    ("bug-fix", "high"): "B",
    ("test", "low"): "A",
    ("test", "medium"): "B",
    ("docs", "low"): "A",
    ("docs", "medium"): "A",
}
_PATH_HIGH_COMPLEXITY: str = "C"  # any task class at high complexity → PATH C

# Budget estimation constants.
_BYTES_PER_QUERY_CHAR: int = 8  # rough heuristic: 8 bytes of context per query char
_BUDGET_MIN_BYTES: int = 5 * 1024  # 5 KB floor
_BUDGET_MAX_BYTES: int = 85 * 1024  # 85 KB ceiling (PATH C)
_LOCAL_CONFIDENCE: float = 0.4  # heuristic estimate; low confidence

# PATH suggestion from estimated budget size.
_PATH_FROM_BUDGET: list[tuple[int, str]] = [
    (40 * 1024, "A"),
    (45 * 1024, "B"),
    (85 * 1024, "C"),
]
