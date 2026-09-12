"""CacheEntry — a single cache entry with timestamp."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    """Single cache entry with timestamp"""

    result: Any  # ContextResult type at runtime
    timestamp: float
    ttl_seconds: int = 300  # 5 minutes
