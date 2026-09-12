"""Pure field helpers and section collectors for governance document generation."""

from __future__ import annotations

from typing import Any


def _fingerprint_prefix(config: dict[str, Any], key: str, size: int = 32) -> str:
    """Return safe fingerprint prefix for template rendering."""
    value = config.get(key)
    if not value and key in {"core_fingerprint", "client_fingerprint"}:
        value = config.get("fingerprint")
    if not value:
        return "N/A"
    return str(value)[:size]


def _item_description(item: dict[str, Any]) -> str:
    """Return non-empty item description for instruction rendering."""
    desc = (
        str(item.get("description") or "").strip()
        or str(item.get("content") or "").strip()
        or str((item.get("metadata") or {}).get("description") or "").strip()
        or str(item.get("summary_minimal") or "").strip()
        or str(item.get("summary_runtime") or "").strip()
    )
    return desc or "(description unavailable)"


def _item_name(item: dict[str, Any]) -> str:
    """Return non-empty item display name, falling back to ID."""
    item_id = str(item.get("id", "")).strip()
    for key in ("name", "title"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return item_id


def _format_rules(rules: list[dict[str, Any]]) -> str:
    """Format rules as markdown list."""
    if not rules:
        return "No mandatory rules defined."

    formatted = []
    for i, rule in enumerate(rules, 1):
        name = rule.get("name", f"Rule {i}")
        description = rule.get("description", "No description")
        formatted.append(f"{i}. **{name}**: {description}")

    return "\n".join(formatted)


def _collect_instruction_sections(
    config: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Group governance items by semantic role for instruction rendering."""
    items: list[dict[str, Any]] = config.get("items", [])

    mandates: list[dict[str, Any]] = []
    guidelines: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    for item in items:
        item_type = str(item.get("type", "")).upper()
        metadata_type = str(item.get("metadata", {}).get("type", "")).upper()
        criticality = str(item.get("metadata", {}).get("criticality", "")).upper()

        if item_type == "MANDATE" or metadata_type == "MANDATE":
            mandates.append(item)
        elif item_type in ("GUIDELINE", "RULE") or metadata_type in (
            "GUIDELINE",
            "RULE",
        ):
            guidelines.append(item)
        elif item_type == "DECISION" or metadata_type == "DECISION":
            decisions.append(item)
        elif criticality in ("MANDATORY", "HARD", "CRITICAL"):
            mandates.append(item)
        elif criticality in ("RECOMMENDED", "SOFT", "GUIDELINE"):
            guidelines.append(item)
        else:
            guidelines.append(item)

    return {
        "items": items,
        "mandates": mandates,
        "guidelines": guidelines,
        "decisions": decisions,
    }
