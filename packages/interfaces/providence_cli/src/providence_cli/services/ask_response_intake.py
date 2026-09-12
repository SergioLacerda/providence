"""ask_response_intake  structured intake/intent classification for `providence ask`.

Split out of `ask_response.py`/`ask_response_json.py` (T4,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`): these
are the intake-classification helpers shared by both the text and JSON
response paths, plus the JSON-path intake-only responder that depends on them.

The five classification/gate/routing functions below (and
`_looks_like_implementation_intent`, `ASK_ENTRYPOINT_ENV`) were relocated to
`providence_runtime.intake` per
`.analysis/pending/20260907-backend-governance-reorg-refinement` (Fase 1).
They are re-exported here unchanged so existing callers and test
`mock.patch` targets at this module path keep working unmodified  this is a
deliberate, temporary compatibility seam, not the end state.
"""

from __future__ import annotations

from typing import Any

from providence_runtime.intake import (
    ASK_ENTRYPOINT_ENV,
    _looks_like_implementation_intent,
    build_intake_contract_fields,
    classify_ask_intent,
    resolve_ask_entrypoint,
    resolve_ask_next_action,
    resolve_execution_gate,
)

from providence_cli.services.ask_hash import _hash_query
from providence_cli.services.ask_types import _AskInputs, _AskSessionContext
from providence_cli.utils.output import emit_json

__all__ = [
    "ASK_ENTRYPOINT_ENV",
    "_looks_like_implementation_intent",
    "build_intake_contract_fields",
    "classify_ask_intent",
    "emit_ask_intake_only_json_response",
    "resolve_ask_entrypoint",
    "resolve_ask_next_action",
    "resolve_execution_gate",
]


def emit_ask_intake_only_json_response(
    inputs: _AskInputs,
    session: _AskSessionContext,
    *,
    runtime_handbook_hint: dict[str, Any] | None = None,
) -> None:
    """Cheap hook-mode JSON response: gate + structured intent only.

    Deliberately omits fingerprint, mandates_loaded, degraded/drift status,
    trust_source, and full runtime_handbook payloads  those require the full
    governance snapshot this profile exists to avoid loading (spike:
    20260714-sdd-ask-single-entrypoint-spike, A-005/I-005). A compact
    runtime_handbook_hint may be present when a runtime-only lookup finds an
    opportunistic runbook signal.
    """
    execution_gate = resolve_execution_gate(
        organize_used=session.organize_used,
        organize_reason=session.organize_reason,
    )
    intake_contract = build_intake_contract_fields(
        execution_gate=execution_gate, query=inputs.query, skill=inputs.skill
    )
    data: dict[str, Any] = {
        "profile": session.profile,
        "query_hash": _hash_query(inputs.query),
        "intake_index_mode": "multi" if session.organize_used else "none",
        "intake_chunks": session.organize_chunks,
        "intake_retrieval": session.organize_retrieval,
        "intake_artifact": session.organize_artifact_path or "n/a",
        "governance_mode": "hard",
        "execution_gate": execution_gate,
        "intake_profile": "cheap",
        **intake_contract,
    }
    if runtime_handbook_hint:
        data["runtime_handbook_hint"] = runtime_handbook_hint
    emit_json(
        {
            "status": "ok",
            "command": "ask",
            "ok": True,
            "error": None,
            "data": data,
        }
    )
