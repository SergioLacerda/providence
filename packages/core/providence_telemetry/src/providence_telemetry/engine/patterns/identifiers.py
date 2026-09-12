"""Patterns for identifier fields: UUIDs, hashes, API keys, tokens, and slugs."""

from providence_telemetry.types import PatternDef

IDENTIFIER_PATTERNS: dict[str, PatternDef] = {
    "ID001": {
        "name": "UUID Format",
        "regex": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        "fields": [
            "id",
            "entity_id",
            "trace_id",
            "request_id",
            "correlation_id",
            "session_id",
        ],
        "compression_ratio": 0.44,
        "frequency": 0.75,
    },
    "ID002": {
        "name": "Numeric ID",
        "regex": r"^[0-9]{1,19}$",
        "fields": ["id", "entity_id", "user_id", "order_id"],
        "compression_ratio": 0.08,
        "frequency": 0.60,
    },
    "ID003": {
        "name": "Alphanumeric ID",
        "regex": r"^[A-Z0-9]{8,}$",
        "fields": ["code", "reference", "token"],
        "compression_ratio": 0.15,
        "frequency": 0.45,
    },
    "ID004": {
        "name": "SHA256 Hash",
        "regex": r"^[a-f0-9]{64}$",
        "fields": ["hash", "sha256", "checksum", "fingerprint"],
        "compression_ratio": 0.50,
        "frequency": 0.35,
    },
    "ID005": {
        "name": "MD5 Hash",
        "regex": r"^[a-f0-9]{32}$",
        "fields": ["hash", "md5", "checksum"],
        "compression_ratio": 0.35,
        "frequency": 0.20,
    },
    "ID006": {
        "name": "API Key Format",
        "regex": r"^[a-zA-Z0-9_-]{32,}$",
        "fields": ["api_key", "secret_key", "token", "auth_token"],
        "compression_ratio": 0.40,
        "frequency": 0.25,
    },
    "ID007": {
        "name": "Base64 Encoded",
        "regex": r"^[A-Za-z0-9+/]*={0,2}$",
        "fields": ["encoded", "data", "payload"],
        "compression_ratio": 0.30,
        "frequency": 0.30,
    },
    "ID008": {
        "name": "GUID (Windows)",
        "regex": r"^\{[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\}$",
        "fields": ["guid", "id"],
        "compression_ratio": 0.48,
        "frequency": 0.10,
    },
    "ID009": {
        "name": "Slug Format",
        "regex": r"^[a-z0-9]+(-[a-z0-9]+)*$",
        "fields": ["slug", "name", "key"],
        "compression_ratio": 0.12,
        "frequency": 0.40,
    },
    "ID010": {
        "name": "JWT Token",
        "regex": r"^eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$",
        "fields": ["token", "jwt", "auth_header"],
        "compression_ratio": 0.55,
        "frequency": 0.50,
    },
}
