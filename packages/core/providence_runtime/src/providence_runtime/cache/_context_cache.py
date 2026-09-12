"""ContextCache — in-memory LRU cache for ContextLoader results."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from ._entry import CacheEntry


class ContextCache:
    """In-memory LRU cache for ContextLoader results"""

    def __init__(self, max_size: int = 128, ttl_seconds: int = 300):
        """Initialize cache

        Args:
            max_size: Maximum number of cached results (default: 128)
            ttl_seconds: Time-to-live for cache entries in seconds (default: 300 / 5 min)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: dict[str, CacheEntry] = {}
        self.hit_count = 0
        self.miss_count = 0

    @staticmethod
    def _make_key(
        artifact_id: str | None,
        query: str,
        max_items: int,
        item_types: list[str],
        budget_utilization_pct: float = 0.0,
    ) -> str:
        """Generate cache key from request parameters

        Args:
            artifact_id: Compiled artifact ID (or None for fallback)
            query: Search query string
            max_items: Maximum items to return
            item_types: Item type filters
            budget_utilization_pct: Budget utilization percentage (affects compression)

        Returns:
            Hash-based cache key

        Fingerprint domain (SEC-08,
        `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`):
        purpose=in-memory LRU cache key (not an integrity or identity
        fingerprint), algorithm=sha256, normalization=colon-joined request
        params with `budget_utilization_pct` rounded to one decimal,
        length=full 64-char hex (unlike the codebase's other, truncated
        fingerprint domains — this one is not shortened, but it is still a
        distinct domain: a cache key, comparable only to another cache key
        built from `_make_key`, never to a governance/integrity fingerprint).
        """
        key_str = f"{artifact_id}:{query}:{max_items}:{','.join(sorted(item_types))}:{budget_utilization_pct:.1f}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(
        self,
        artifact_id: str | None,
        query: str,
        max_items: int,
        item_types: list[str],
        budget_utilization_pct: float = 0.0,
    ) -> Any | None:
        """Retrieve cached result if valid

        Args:
            artifact_id: Artifact ID for lookup
            query: Search query
            max_items: Max items requested
            item_types: Item type filters
            budget_utilization_pct: Budget utilization percentage (affects compression)

        Returns:
            Cached ContextResult if hit and not expired, else None
        """
        key = self._make_key(
            artifact_id, query, max_items, item_types, budget_utilization_pct
        )
        entry = self.cache.get(key)

        if entry is None:
            self.miss_count += 1
            return None

        # Check TTL
        elapsed = time.time() - entry.timestamp
        if elapsed > entry.ttl_seconds:
            # Expired, remove and return miss
            del self.cache[key]
            self.miss_count += 1
            return None

        self.hit_count += 1
        return entry.result

    def set(
        self,
        artifact_id: str | None,
        query: str,
        max_items: int,
        item_types: list[str],
        result: Any,
        budget_utilization_pct: float = 0.0,
    ) -> None:
        """Cache a result

        Args:
            artifact_id: Artifact ID for storage
            query: Search query
            max_items: Max items
            item_types: Item type filters
            result: ContextResult to cache
            budget_utilization_pct: Budget utilization percentage (affects compression)
        """
        key = self._make_key(
            artifact_id, query, max_items, item_types, budget_utilization_pct
        )

        # Simple LRU: if at capacity, remove oldest entry
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].timestamp,
            )
            del self.cache[oldest_key]

        self.cache[key] = CacheEntry(
            result=result,
            timestamp=time.time(),
            ttl_seconds=self.ttl_seconds,
        )

    def stats(self) -> dict[str, Any]:
        """Get cache statistics

        Returns:
            Dict with hit/miss counts and hit rate
        """
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total * 100) if total > 0 else 0.0

        return {
            "hits": self.hit_count,
            "misses": self.miss_count,
            "hit_rate_pct": hit_rate,
            "entries": len(self.cache),
            "max_size": self.max_size,
        }

    def clear(self) -> None:
        """Clear all cached entries"""
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0
