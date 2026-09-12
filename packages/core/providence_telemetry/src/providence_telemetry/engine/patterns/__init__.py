"""Aggregates all built-in pattern sets into a single registry-ready dict."""

from providence_telemetry.types import PatternDef

from .identifiers import IDENTIFIER_PATTERNS
from .messages import MESSAGE_PATTERNS
from .metadata import METADATA_PATTERNS
from .network import NETWORK_PATTERNS
from .temporal import TEMPORAL_PATTERNS
from .types import TYPE_PATTERNS


def get_all_patterns() -> dict[str, PatternDef]:
    """Return every built-in PatternDef keyed by pattern ID."""
    return {
        **TEMPORAL_PATTERNS,
        **NETWORK_PATTERNS,
        **IDENTIFIER_PATTERNS,
        **TYPE_PATTERNS,
        **MESSAGE_PATTERNS,
        **METADATA_PATTERNS,
    }


__all__ = [
    "get_all_patterns",
    "TEMPORAL_PATTERNS",
    "NETWORK_PATTERNS",
    "IDENTIFIER_PATTERNS",
    "TYPE_PATTERNS",
    "MESSAGE_PATTERNS",
    "METADATA_PATTERNS",
]
