"""Signature manifest schema validation."""

from __future__ import annotations

import re
from typing import Any

_KEY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._:-]{3,128}$")
_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _validate_manifest_schema(sig: dict[str, Any]) -> str | None:
    required = {
        "schema_version",
        "algorithm",
        "key_id",
        "artifact_name",
        "profile",
        "payload_hash",
        "signature",
        "signed_at",
    }
    missing = sorted(required - set(sig.keys()))
    if missing:
        return f"missing required fields: {missing}"
    if str(sig.get("schema_version")) != "1.0":
        return "schema_version must be '1.0'"
    if str(sig.get("algorithm")) != "ed25519":
        return "algorithm must be 'ed25519'"
    key_id = str(sig.get("key_id", ""))
    if not _KEY_ID_PATTERN.match(key_id):
        return "invalid key_id pattern"
    profile = str(sig.get("profile", ""))
    if profile not in {"master", "client"}:
        return "profile must be master|client"
    payload_hash = str(sig.get("payload_hash", ""))
    if not _HEX64_PATTERN.match(payload_hash):
        return "payload_hash must be lowercase hex sha256"
    if not str(sig.get("signature", "")).strip():
        return "signature must be non-empty base64"
    if not str(sig.get("signed_at", "")).endswith("Z"):
        return "signed_at must be RFC3339 UTC timestamp ending with Z"
    return None
