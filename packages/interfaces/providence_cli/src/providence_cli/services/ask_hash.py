"""Shared hash helpers for `providence ask` payloads and telemetry."""

from __future__ import annotations

import hashlib


def _hash_query(query: str) -> str:
    """Return the stable short query hash used by ask outputs."""
    return hashlib.sha256(query.encode()).hexdigest()[:8]
