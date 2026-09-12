"""ContextResult — result of a context loading operation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ContextResult:
    """Result of a context loading operation."""

    items: list[str]
    source: str  # "artifact" | "fallback"
    matched: int
    truncated: bool
    bytes_loaded: int = 0  # total UTF-8 bytes of returned items (§economy/metrics.md)
    compression_ratio: float | None = (
        None  # compression ratio if compression applied; None if not
    )
    compression_attempted: bool = False  # True whenever the YELLOW/RED-zone branch ran
    compression_failure_code: str | None = (
        None  # raised exception's class name when compression was attempted and failed
    )
