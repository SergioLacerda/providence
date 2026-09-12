"""
Delta context computation for skill routing.
Reference: skillsV6.md §3.4

Determines whether the execution context has changed since the last run,
enabling minimal dossier generation instead of full context reload.
All hashing is deterministic (sha256, sorted inputs).
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Final

DEFAULT_TTL_SECONDS: Final[int] = 300


@dataclass(frozen=True)
class ContextSignature:
    """ContextSignature."""

    scope_hash: str  # sha256 of sorted scope paths
    registry_fingerprint: str
    active_rules: tuple[str, ...]  # sorted "id@version" strings
    computed_at: float  # unix timestamp

    def is_expired(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
        """Is Expired."""
        return (time.time() - self.computed_at) > ttl_seconds

    def matches(self, other: ContextSignature) -> bool:
        """Compare structural fields only (not computed_at)."""
        return (
            self.scope_hash == other.scope_hash
            and self.registry_fingerprint == other.registry_fingerprint
            and self.active_rules == other.active_rules
        )


@dataclass
class ContextCache:
    """In-memory cache of context signatures per task scope."""

    _store: dict[str, ContextSignature] = field(default_factory=dict)

    def get(self, cache_key: str) -> ContextSignature | None:
        """Get."""
        return self._store.get(cache_key)

    def set(self, cache_key: str, signature: ContextSignature) -> None:
        """Set."""
        self._store[cache_key] = signature

    def invalidate(self, cache_key: str) -> None:
        """Invalidate."""
        self._store.pop(cache_key, None)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def compute_scope_hash(scope_paths: list[str]) -> str:
    """
    Deterministic hash of scope paths.
    Sorting ensures path order doesn't affect the hash.
    """
    normalized = "|".join(sorted(scope_paths))
    return _sha256(normalized)


def compute_context_signature(
    scope_paths: list[str],
    registry_fingerprint: str,
    active_rule_ids: list[str],
) -> ContextSignature:
    """
    Compute a fully deterministic context signature.

    active_rule_ids should be "id@version" strings (e.g. "scope_locking@1.2.0").
    Sorting ensures order doesn't affect the signature.
    """
    return ContextSignature(
        scope_hash=compute_scope_hash(scope_paths),
        registry_fingerprint=registry_fingerprint,
        active_rules=tuple(sorted(active_rule_ids)),
        computed_at=time.time(),
    )


def compute_input_signature(
    intent_normalized: str,
    scope_paths: list[str],
    registry_fingerprint: str,
) -> str:
    """
    Routing cache key. Deterministic given same inputs.
    Used by /ask to skip re-routing for identical requests.
    """
    scope_hash = compute_scope_hash(scope_paths)
    raw = f"{intent_normalized}|{scope_hash}|{registry_fingerprint}"
    return _sha256(raw)


def is_delta_context(
    current: ContextSignature,
    cached: ContextSignature | None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> bool:
    """
    Return True if cached context is still valid (only NEW: items need to be sent).
    Return False if full context reload is required.
    """
    if cached is None:
        return False
    if cached.is_expired(ttl_seconds):
        return False
    return cached.matches(current)
