"""Deterministic fingerprinting for governance artifacts."""

from __future__ import annotations

import hashlib
import json
from typing import Any


class GovernanceFingerprinter:
    """Generates deterministic SHA-256 fingerprints for governance items.

    Fingerprint domain (SEC-08,
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`):
    purpose=integrity/identity of a governance-item set, algorithm=sha256,
    normalization=sorted-by-id canonical JSON, length=full 64-char hex
    digest (never truncated). This is the "full digest for integrity
    decisions" domain the SEC-08 finding contrasts with the codebase's
    other, shorter, differently-normalized hashes — e.g.
    `ask_context_drift.compute_routing_signature` (16-char cache key,
    explicitly not a signature) and `HandshakeCache.compute_spec_fingerprint`
    (16-char governance-version fingerprint). Comparing a value from one
    domain against another (mismatched purpose, algorithm, normalization,
    or length) is a category error, not a meaningful equality check — see
    DRF-02 for a concrete historical instance of that exact bug.
    """

    HASH_ALGORITHM = "sha256"

    @staticmethod
    def generate(items: list[dict[str, Any]], salt: str = "") -> str:
        """Generate a deterministic SHA-256 hash using canonical JSON serialization.

        Args:
            items: List of governance items to hash
            salt: Optional salt string to mix into the hash

        Returns:
            SHA-256 hex digest, or "empty" if no items and no salt
        """
        if not items and not salt:
            return "empty"

        # Ensure deterministic order
        sorted_items = sorted(items, key=lambda x: x.get("id", ""))

        # Canonical JSON string (sorted keys, fixed separators)
        canonical_json = json.dumps(
            sorted_items, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

        payload = canonical_json + salt
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
