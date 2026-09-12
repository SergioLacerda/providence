"""Consultive runtime handbook lookup.

Split out of `governance_docs_sources.py` (T7,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from providence_cli.services.governance_docs_sources import (
    DEFAULT_HANDBOOK_DIR,
    HandbookLookupReport,
    _load_yaml,
)


def _matches_any(candidate_values: Any, requested_values: set[str]) -> bool:
    if not requested_values:
        return True
    if not isinstance(candidate_values, list):
        return False
    candidate_set = {str(item) for item in candidate_values}
    return bool(candidate_set & requested_values)


def _load_handbook_item(root: Path, runtime_doc: str) -> dict[str, Any] | None:
    path = root / runtime_doc
    if not path.exists():
        return None
    data = _load_yaml(path)
    return data if data else None


def _entry_matches_lookup(
    entry: dict[str, Any],
    *,
    task_types: set[str],
    phases: set[str],
    refs: set[str],
    risks: set[str],
) -> bool:
    return (
        _matches_any(entry.get("task_types"), task_types)
        and _matches_any(entry.get("operation_phases"), phases)
        and _matches_any(entry.get("mandate_refs"), refs)
        and (not risks or _matches_any(entry.get("risk_levels"), risks))
    )


def _handbook_match_payload(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    """Build one lookup match payload.

    CTX-07 (`.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`):
    `load_policy` here is metadata carried through from the handbook entry
    this lookup does not itself apply any token ceiling, truncate content,
    or rank matches by relevance beyond the `limit` cap and match order in
    `lookup_runtime_handbook`. A caller that needs a token budget enforced
    must apply `load_policy` itself before loading `runtime_doc`'s full
    content; treating this payload's presence as proof a limit was already
    enforced is a misreading of the contract.
    """
    runtime_doc = str(entry.get("runtime_doc", ""))
    item = _load_handbook_item(root, runtime_doc) if runtime_doc else None
    return {
        "id": str(entry.get("id", "")),
        "title": str(entry.get("title", "")),
        "source_doc": str(entry.get("source_doc", "")),
        "runtime_doc": runtime_doc,
        "mandate_refs": list(entry.get("mandate_refs", [])),
        "task_types": list(entry.get("task_types", [])),
        "operation_phases": list(entry.get("operation_phases", [])),
        "risk_levels": list(entry.get("risk_levels", [])),
        "load_policy": item.get("load_policy", {}) if item else {},
        "summary": str(item.get("summary", "")) if item else "",
    }


def lookup_runtime_handbook(
    root: Path,
    *,
    task_type: str | None = None,
    mandate_refs: list[str] | None = None,
    operation_phase: str | None = None,
    risk_level: str | None = None,
    limit: int = 5,
) -> HandbookLookupReport:
    """Lookup consultive runtime handbook entries without scanning docs/.

    Filters entries by task type, mandate refs, operation phase, and risk
    level, capped to `limit` matches. This does not apply, or even inspect,
    any match's `load_policy` token ceiling, and does not rank matches by
    semantic relevance  it returns entries in index order up to `limit`.
    Budget enforcement is the caller's responsibility (CTX-07,
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`).
    """
    index_path = root / DEFAULT_HANDBOOK_DIR / "index.yaml"
    if not index_path.exists():
        return HandbookLookupReport(
            status="missing",
            diagnostic="handbook_index_missing",
            matches=[],
        )

    index = _load_yaml(index_path)
    entries = index.get("items", [])
    if not isinstance(entries, list):
        return HandbookLookupReport(
            status="invalid",
            diagnostic="handbook_index_invalid",
            matches=[],
        )

    task_types = {task_type} if task_type else set()
    phases = {operation_phase} if operation_phase else set()
    refs = set(mandate_refs or [])
    risks = {risk_level} if risk_level else set()
    matches: list[dict[str, Any]] = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if not _entry_matches_lookup(
            entry,
            task_types=task_types,
            phases=phases,
            refs=refs,
            risks=risks,
        ):
            continue
        matches.append(_handbook_match_payload(root, entry))
        if len(matches) >= limit:
            break

    if not matches:
        return HandbookLookupReport(
            status="none",
            diagnostic="handbook_match=none",
            matches=[],
        )
    return HandbookLookupReport(
        status="matched",
        diagnostic=f"handbook_match={len(matches)}",
        matches=matches,
    )
