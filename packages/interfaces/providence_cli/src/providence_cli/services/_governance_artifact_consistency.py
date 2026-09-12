"""Artifact consistency helpers for governance handlers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from providence_cli.utils.loader import resolve_governance_compiled_dir


def _safe_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _load_consistency_artifacts(
    compiled_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    audit_dir = compiled_dir / "audit"
    core_json = _safe_json(compiled_dir / "governance-core.json") or _safe_json(
        audit_dir / "governance-core.json"
    )
    client_json = _safe_json(compiled_dir / "governance-client.json") or _safe_json(
        audit_dir / "governance-client.json"
    )
    core_meta = _safe_json(audit_dir / "metadata-core.json") or _safe_json(
        compiled_dir / "metadata-core.json"
    )
    client_meta = _safe_json(audit_dir / "metadata-client-template.json") or _safe_json(
        compiled_dir / "metadata-client-template.json"
    )
    if any(item is None for item in (core_json, client_json, core_meta, client_meta)):
        return None
    assert core_json is not None
    assert client_json is not None
    assert core_meta is not None
    assert client_meta is not None
    return core_json, client_json, core_meta, client_meta


def _count_items_by_type(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        item_type = str(item.get("type", "UNKNOWN")).upper()
        counts[item_type] = counts.get(item_type, 0) + 1
    return counts


def _has_malformed_titles(items: list[dict[str, Any]]) -> bool:
    for item in items:
        title = str(item.get("title") or "").strip().lower()
        if title.startswith("- status:"):
            return True
    return False


def _validate_payload_vs_metadata(
    payload: dict[str, Any], metadata: dict[str, Any], label: str
) -> str | None:
    items = payload.get("items", [])
    if not isinstance(items, list):
        return "invalid payload schema: items must be a list"
    if payload.get("fingerprint") != metadata.get("fingerprint"):
        return f"{label} fingerprint mismatch between payload and metadata"
    if int(metadata.get("item_count", -1)) != len(items):
        return f"{label} item_count mismatch"
    if _count_items_by_type(items) != dict(metadata.get("items_by_type", {})):
        return f"{label} items_by_type mismatch"
    if label == "core" and _has_malformed_titles(items):
        return "malformed mandate title detected"
    return None


def check_artifact_consistency(
    path: str,
    *,
    resolve_compiled_dir_fn: Any = resolve_governance_compiled_dir,
) -> tuple[bool, str]:
    """Cross-check compiled governance JSON and metadata consistency."""
    compiled_dir = resolve_compiled_dir_fn(path)
    if compiled_dir is None:
        return (
            False,
            f"could not resolve compiled governance directory at {path} (check path policy or missing artifacts)",
        )
    loaded = _load_consistency_artifacts(compiled_dir)
    if loaded is None:
        return False, "missing governance JSON or metadata artifacts"
    core_json, client_json, core_meta, client_meta = loaded

    core_issue = _validate_payload_vs_metadata(core_json, core_meta, "core")
    if core_issue:
        return False, core_issue
    client_issue = _validate_payload_vs_metadata(client_json, client_meta, "client")
    if client_issue:
        return False, client_issue
    if client_json.get("fingerprint_core_salt") != client_meta.get(
        "fingerprint_core_salt"
    ):
        return False, "client fingerprint_core_salt mismatch"
    # Internal consistency alone (declared count == actual count) passes even
    # when both are 0  a silent, empty client governance compile that
    # `_governance_orchestrator_support.pipeline_checks()`'s "Client items >
    # 0" check catches during `governance compile`/`generate`, but this
    # `check_artifact_consistency()` path (also used by `governance
    # validate`) never did, so a `validate`-only run over an already-compiled
    # 0-item artifact reported healthy. See
    # .analysis/pending/20260906-governance-validate-coverage-check.md.
    client_items = client_json.get("items", [])
    if isinstance(client_items, list) and len(client_items) == 0:
        return (
            False,
            "client governance has 0 items (guideline compilation may have failed silently)",
        )
    return True, "ok"
