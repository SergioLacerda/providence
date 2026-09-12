"""Governance item type resolution helpers."""

from __future__ import annotations


def _resolve_item_type(
    raw_item: dict[str, object], meta_block: dict[str, object]
) -> tuple[str, str]:
    """Resolve governance item type with explicit source precedence.

    Precedence:
    1) top-level ``type`` (canonical)
    2) ``metadata.type`` (legacy fallback)
    3) ``UNKNOWN``
    """
    top_level = str(raw_item.get("type", "")).strip()
    if top_level:
        return _normalize_item_type(top_level), "type"

    metadata_type = str(meta_block.get("type", "")).strip()
    if metadata_type:
        return _normalize_item_type(metadata_type), "metadata.type"

    return "UNKNOWN", "missing"


def _normalize_item_type(value: str) -> str:
    normalized = value.upper().strip()
    if normalized.startswith("-"):
        normalized = normalized.lstrip("- ").strip()
    return normalized or "UNKNOWN"
