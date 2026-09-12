"""
Runtime Context Caching — In-Memory LRU Cache for Hot Queries

Provides in-memory caching for frequently accessed governance artifacts to reduce
I/O overhead and improve latency for repeated context loading requests.

Cache policy:
  - Max size: 128 artifacts
  - TTL: 5 minutes
  - Eviction: LRU (Least Recently Used)
  - Key: hash(artifact_id, query, max_items, item_types)
"""

from __future__ import annotations

from ._context_cache import ContextCache
from ._decorator import _context_cache, cached_load, get_context_cache
from ._entry import CacheEntry

__all__ = [
    "CacheEntry",
    "ContextCache",
    "_context_cache",
    "cached_load",
    "get_context_cache",
]
