"""providence ask  cheap runtime handbook hint lookup (cached).

Split out of `_pipeline.py` (T9,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from providence_runtime.cache import get_context_cache

_HANDBOOK_LOOKUP_LIMIT = 5
_RUNBOOK_HANDBOOK_ID = "HBK-RUNBOOK-CONSULTATION"
_RUNBOOK_SIGNAL_TOKENS = (
    "diagnos",
    "erro",
    "error",
    "fail",
    "failure",
    "falha",
    "hotfix",
    "recovery",
    "recover",
    "recuper",
    "release",
    "asset",
    "runtime drift",
    "drift",
    "generated-runtime",
    "generated runtime",
    "governance runtime",
    "context budget",
    "token budget",
    "budget breach",
    "estouro de contexto",
    "oramento de contexto",
)


def _cached_handbook_lookup(
    root: Path, *, query: str, task_type: str, operation_phase: str
) -> Any:
    """Look up runtime handbook entries via the shared `ContextLoader` cache.

    The default `providence ask` snapshot path re-read and re-matched
    `index.yaml` on every call with zero caching benefit, unlike `--dossier`
    (which already uses this same in-memory LRU cache, 128 entries/5-min TTL,
    via `ContextLoader`). Reusing that cache here  keyed on the query plus
    task_type/operation_phase  avoids re-parsing the handbook index for a
    repeated/near-identical query within the TTL window.
    """
    from providence_cli.services.governance_docs_handbook_lookup import (
        lookup_runtime_handbook,
    )

    cache = get_context_cache()
    artifact_id = f"handbook:{root.resolve()}"
    item_types = [task_type, f"phase:{operation_phase}"]
    cached = cache.get(artifact_id, query, _HANDBOOK_LOOKUP_LIMIT, item_types)
    if cached is not None:
        return cached
    result = lookup_runtime_handbook(
        root, task_type=task_type, operation_phase=operation_phase
    )
    cache.set(artifact_id, query, _HANDBOOK_LOOKUP_LIMIT, item_types, result)
    return result


def _infer_handbook_task_type(query: str, skill: str | None) -> str:
    skill_value = (skill or "").strip().lower()
    if skill_value in {"planning", "implementation", "diagnosis"}:
        return skill_value
    if skill_value in {"diagnose", "debug", "stabilize"}:
        return "diagnosis"
    query_value = query.lower()
    if any(token in query_value for token in ("diagnos", "erro", "error", "fail")):
        return "diagnosis"
    if any(token in query_value for token in ("plan", "design", "proposal")):
        return "planning"
    return "implementation"


def _runbook_relevance_reason(query: str) -> str | None:
    query_value = query.casefold()
    matched = [token for token in _RUNBOOK_SIGNAL_TOKENS if token in query_value]
    if not matched:
        return None
    return f"runtime runbook signal matched: {', '.join(matched[:3])}"


def _compact_handbook_match(match: dict[str, Any]) -> dict[str, Any]:
    hint: dict[str, Any] = {
        "id": str(match.get("id", "")),
        "runtime_doc": str(match.get("runtime_doc", "")),
    }
    load_policy = match.get("load_policy")
    if isinstance(load_policy, dict) and load_policy:
        hint["load_policy"] = load_policy
    return hint


def build_runtime_handbook_hint(
    *,
    root: Path,
    query: str,
    skill: str | None,
    cached_handbook_task_type: str | None = None,
) -> dict[str, Any] | None:
    """Return a compact runtime-only handbook hint for cheap ask profiles.

    This is intentionally narrower than the full governed snapshot. It reads only
    generated runtime handbook files under `.providence/source/handbook/**`, and it
    emits a hint only when the query has operational/runbook symptoms.
    """
    relevance_reason = _runbook_relevance_reason(query)
    if relevance_reason is None:
        return None
    handbook_task_type = (
        cached_handbook_task_type
        if cached_handbook_task_type is not None
        else _infer_handbook_task_type(query, skill)
    )
    try:
        lookup = _cached_handbook_lookup(
            root,
            query=query,
            task_type=handbook_task_type,
            operation_phase="context_loading",
        )
    except Exception as exc:
        return {
            "status": "skipped",
            "diagnostic": f"handbook_lookup_error:{type(exc).__name__}",
            "relevance_reason": relevance_reason,
        }
    matches = list(getattr(lookup, "matches", []))
    selected = next(
        (
            match
            for match in matches
            if str(match.get("id", "")) == _RUNBOOK_HANDBOOK_ID
        ),
        matches[0] if matches else None,
    )
    hint: dict[str, Any] = {
        "status": getattr(lookup, "status", "unknown"),
        "diagnostic": getattr(lookup, "diagnostic", ""),
        "relevance_reason": relevance_reason,
    }
    if isinstance(selected, dict):
        hint.update(_compact_handbook_match(selected))
    return hint
