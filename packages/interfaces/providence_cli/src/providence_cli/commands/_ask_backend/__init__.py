"""providence ask  governed context query command.

Security:
  - Query text is NEVER logged; only sha256[:8] hash is recorded.
  - trace_id is uuid4 local-only; no external correlation.
  - Compliance JSONL is append-only at .providence/runtime/compliance-events.jsonl.
"""

from __future__ import annotations

from contextvars import ContextVar

import typer

__all__ = [
    "app",
    "_JSON_MODE_OVERRIDE",
    "ask_cmd",
    "_ask_cmd_impl",
    "build_runtime_handbook_hint",
    "build_governed_ask_snapshot",
    "run_sdd_organize",
    "_should_use_organize",
    "_resolve_tokens",
    "_capture_effective_tokens",
    "_emit_ask_telemetry",
    "_build_ask_telemetry_sink",
    "_enqueue_flush",
    "_resolve_workspace_root",
    "_get_profile_state",
    "_run_organize_intake",
    "_render_context_output",
    "_try_sdd_compiled_dir",
    "_hash_query",
    "_load_compiled_governance",
    "_normalize_typer_value",
    "_check_fingerprint_drift",
    "_get_cached_governance_snapshot",
    "_get_last_known_fingerprint",
    "_write_runtime_cache",
    "_write_runtime_cache_and_routing_decision",
    "_resolve_routing_decision",
    "_store_routing_decision",
    "_upsert_ask_session",
    "_emit_state_warnings",
    "_governance_footer_for_state",
    "_guard_budget_breach",
    "_guard_handshake",
    "_runtime_drift_check",
    "_root_seed_drift_check",
    "_build_dossier_lines",
    "_load_dossier_artifact",
    "TelemetrySink",
    "OtelBridge",
    "OtlpHttpExporter",
]

app: typer.Typer = typer.Typer(help="Query Providence governance context.")

_JSON_MODE_OVERRIDE: ContextVar[bool | None] = ContextVar(
    "ask_json_mode_override", default=None
)


from ._budget import _guard_budget_breach, _guard_handshake  # noqa: E402
from ._helpers import (  # noqa: E402
    _check_fingerprint_drift,
    _get_cached_governance_snapshot,
    _get_last_known_fingerprint,
    _get_profile_state,
    _governance_footer_for_state,
    _hash_query,
    _load_compiled_governance,
    _normalize_typer_value,  # noqa: E402
    _render_context_output,
    _resolve_routing_decision,
    _resolve_workspace_root,
    _root_seed_drift_check,
    _runtime_drift_check,
    _store_routing_decision,
    _try_sdd_compiled_dir,
    _write_runtime_cache,
    _write_runtime_cache_and_routing_decision,
)
from ._pipeline import (  # noqa: E402
    _should_use_organize,
    ask_cmd,
    run_sdd_organize,
)
from ._pipeline_handbook import build_runtime_handbook_hint  # noqa: E402
from ._pipeline_runtime import _ask_cmd_impl  # noqa: E402
from ._pipeline_session import (  # noqa: E402
    _emit_state_warnings,
    _run_organize_intake,
)
from ._pipeline_snapshot import build_governed_ask_snapshot  # noqa: E402
from ._telemetry import (  # noqa: E402
    OtelBridge,
    OtlpHttpExporter,
    TelemetrySink,
    _build_ask_telemetry_sink,
    _build_dossier_lines,
    _capture_effective_tokens,
    _emit_ask_telemetry,
    _enqueue_flush,
    _resolve_tokens,
    _upsert_ask_session,
)
from ._telemetry_dossier import _load_dossier_artifact  # noqa: E402
