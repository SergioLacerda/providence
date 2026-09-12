"""Item rendering and matching helpers for ContextLoader."""

from __future__ import annotations

from ..artifacts import CompiledArtifact, GovernanceItem


def _render_item(
    item: GovernanceItem,
    budget_utilization_pct: float | None,
    *,
    prefer_full_summary: bool = False,
) -> str:
    """Render a governance item with budget-aware verbosity.

    Progressive disclosure based on budget utilization zone:
    - RED zone (>90%): summary_minimal (one-liner, ~35 tokens)
    - YELLOW zone (70-90%): summary_runtime (enforcement rules, ~120 tokens)
    - GREEN zone (<70%): id: title (default), optional summary_full
    """
    if budget_utilization_pct is not None:
        summary_minimal = getattr(item, "summary_minimal", None)
        summary_runtime = getattr(item, "summary_runtime", None)
        if budget_utilization_pct > 90.0 and summary_minimal:
            return str(summary_minimal)
        if budget_utilization_pct >= 70.0 and summary_runtime:
            return str(summary_runtime)
    if prefer_full_summary:
        summary_full = getattr(item, "summary_full", None)
        if summary_full:
            return str(summary_full)
    return f"{item.id}: {item.title}"


def _match_items(
    artifact: CompiledArtifact,
    query: str,
    type_filter: list[str],
) -> list[GovernanceItem]:
    lower_query = query.lower()
    candidates = artifact.items
    if type_filter:
        upper_types = {t.upper() for t in type_filter}
        candidates = [i for i in candidates if i.item_type.upper() in upper_types]

    # Exact ID match first, then partial matches on ID/title/description.
    exact = [i for i in candidates if i.id.lower() == lower_query]
    if exact:
        return exact

    partial = [
        i
        for i in candidates
        if (
            lower_query in i.id.lower()
            or lower_query in i.title.lower()
            or lower_query in i.description.lower()
        )
    ]
    return partial
