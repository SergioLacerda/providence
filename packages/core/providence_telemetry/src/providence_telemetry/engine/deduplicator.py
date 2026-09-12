"""Event deduplication engine using pattern matching and an LRU hash cache."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from datetime import datetime
from functools import lru_cache
from typing import Any

from providence_telemetry.types import CompressionMetrics

from .cache import LRUCache
from .registry import PatternRegistry

_ISO_DATE_RE = re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}")
_UNIX_EPOCH_RE = re.compile(r"^\d{10,13}$")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@lru_cache(maxsize=1024)
def _is_timestamp_like(value: str) -> bool:
    if len(value) >= 10 and _UNIX_EPOCH_RE.match(value):
        return True
    return len(value) >= 19 and bool(_ISO_DATE_RE.match(value))


@lru_cache(maxsize=1024)
def _is_uuid_like(value: str) -> bool:
    return bool(_UUID_RE.match(value.lower()))


@lru_cache(maxsize=1024)
def _encode_timestamp(value: str) -> str:
    if _UNIX_EPOCH_RE.match(value):
        epoch = int(value) // 1000 if len(value) == 13 else int(value)
        return f"#TS:{epoch}"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return f"#TS:{int(dt.timestamp())}"
    except (ValueError, AttributeError):
        return value


class DeduplicationEngine:
    """Replaces known field values with compact pattern tokens to reduce payload size."""

    def __init__(
        self,
        registry: PatternRegistry | None = None,
        cache: LRUCache | None = None,
    ) -> None:
        self._registry = registry if registry is not None else PatternRegistry()
        self._cache = cache if cache is not None else LRUCache()
        self._metrics = CompressionMetrics(0, 0, 0, 0, 0)

    def deduplicate(self, event: dict[str, Any]) -> dict[str, Any]:
        """Return a compressed copy of event, served from cache when identical hash is seen."""
        event_json = json.dumps(event, sort_keys=True, default=str)
        event_hash = hashlib.sha256(event_json.encode()).hexdigest()

        cached = self._cache.get(event_hash)
        if cached is not None:
            self._metrics.cache_hits += 1
            return cached

        self._metrics.cache_misses += 1
        self._metrics.original_size += len(event_json)

        compressed = {}
        for field, value in event.items():
            pattern_id = self._registry.find_pattern(field, value)
            if pattern_id:
                token = f"${pattern_id}"
                compressed[field] = (
                    token if len(token) < len(str(value)) else self._encode_value(value)
                )
                self._metrics.pattern_matches += 1
            else:
                compressed[field] = self._encode_value(value)

        compressed_json = json.dumps(compressed, sort_keys=True, default=str)
        self._metrics.compressed_size += len(compressed_json)

        self._cache.put(event_hash, compressed)
        return dict(compressed)

    def _encode_value(self, value: Any) -> Any:
        """Recursively encode a field value, compressing timestamps and UUIDs to compact tokens."""
        if value is None or isinstance(value, bool | int | float):
            return value
        if isinstance(value, str):
            if _is_timestamp_like(value):
                return _encode_timestamp(value)
            if _is_uuid_like(value):
                return f"#UUID:{value[:8]}..."
            return value
        if isinstance(value, list):
            return [self._encode_value(v) for v in value]
        if isinstance(value, dict):
            return {k: self._encode_value(v) for k, v in value.items()}
        return value

    @staticmethod
    def _is_timestamp_like(value: str) -> bool:
        return _is_timestamp_like(value)

    @staticmethod
    def _is_uuid_like(value: str) -> bool:
        return _is_uuid_like(value)

    @staticmethod
    def _encode_timestamp(value: str) -> str:
        return _encode_timestamp(value)

    def get_metrics(self) -> CompressionMetrics:
        """Return a snapshot copy of the current compression metrics."""
        return replace(self._metrics)

    def reset_metrics(self) -> None:
        """Reset all counters to zero without clearing the event cache."""
        self._metrics = CompressionMetrics(0, 0, 0, 0, 0)

    def clear_cache(self) -> None:
        """Evict all cached events, forcing full reprocessing on next deduplicate call."""
        self._cache.clear()
