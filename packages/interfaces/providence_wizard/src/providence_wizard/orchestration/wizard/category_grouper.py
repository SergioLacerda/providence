"""Pure grouping utilities for mandates and guidelines by category."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def group_by_category(
    items: list[Any], category_attr: str = "category"
) -> dict[str, list[Any]]:
    """Group a list of items by their category attribute."""
    result: dict[str, list[Any]] = defaultdict(list)
    for item in items:
        result[getattr(item, category_attr, "general")].append(item)
    return dict(result)
