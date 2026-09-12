"""Validation helpers for selector export artifacts."""

from __future__ import annotations

import json
from pathlib import Path


class SelectorBridgeError(ValueError):
    """Raised when selector artifacts are invalid."""


def _require_dict(payload: object) -> dict[str, object]:
    if isinstance(payload, dict):
        return payload
    raise SelectorBridgeError("Selector payload must be an object.")


def _require_string_list(value: object, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SelectorBridgeError(f"{field_name} must be a list[str].")
    return list(value)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def validate_selector_selection(
    payload: object,
    *,
    available_ids: set[str] | None = None,
) -> list[str]:
    """Validate a selector export payload and return normalized IDs."""
    data = _require_dict(payload)
    if not isinstance(data.get("version"), str):
        raise SelectorBridgeError("version must be a string.")
    selected_ids = _require_string_list(data.get("selected_ids"), "selected_ids")
    resolved = data.get("resolved_ids", selected_ids)
    resolved_ids = _require_string_list(resolved, "resolved_ids")
    final_ids = _dedupe(resolved_ids)
    if available_ids is None:
        return final_ids
    unknown = [item_id for item_id in final_ids if item_id not in available_ids]
    if unknown:
        joined = ", ".join(unknown)
        raise SelectorBridgeError(f"Unknown selector IDs: {joined}")
    return final_ids


def load_selector_selection(
    path: Path,
    *,
    available_ids: set[str] | None = None,
) -> list[str]:
    """Load and validate selector output from disk."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SelectorBridgeError("Selector payload is not valid JSON.") from exc
    return validate_selector_selection(payload, available_ids=available_ids)
