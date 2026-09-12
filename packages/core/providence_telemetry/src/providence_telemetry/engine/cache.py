"""LRU cache used by the deduplication engine to avoid reprocessing identical events."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from providence_telemetry.constants import DEFAULT_CACHE_SIZE


class LRUCache:
    """Fixed-capacity LRU cache backed by an OrderedDict."""

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE) -> None:
        self._max_size = max_size
        self._store: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def get(self, key: str) -> dict[str, Any] | None:
        """Return the cached value for key, promoting it to MRU, or None on miss."""
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return dict(self._store[key])

    def put(self, key: str, value: dict[str, Any]) -> None:
        """Insert or update key, evicting the LRU entry when at capacity."""
        if self._max_size <= 0:
            return
        if key in self._store:
            self._store.move_to_end(key)
        else:
            if len(self._store) >= self._max_size:
                self._store.popitem(last=False)
        self._store[key] = value

    def clear(self) -> None:
        """Evict all entries."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
