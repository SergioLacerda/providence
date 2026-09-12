"""providence ask  governed snapshot builder.

Split out of `_pipeline.py` (T9,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING, Any

from ._helpers import _signature_mode
from ._helpers_signals import _collect_learning_signals
from ._pipeline_handbook import _cached_handbook_lookup, _infer_handbook_task_type

if TYPE_CHECKING:
    from ._phase_timer import PhaseTimer


def build_governed_ask_snapshot(
    *,
    query: str,
    skill: str | None,
    organize_used: bool,
    workspace_root: Any | None = None,
    require_handshake: bool = True,
    cached_handbook_task_type: str | None = None,
    phase_timer: PhaseTimer | None = None,
) -> dict[str, Any]:
    """Build a governed ask snapshot with envelope + learning context.

    Callers that measure `ask.governance.snapshot` (e.g. `_load_ask_snapshot`)
    own that outer span themselves, wrapping the whole call  this keeps
    that phase observable even when this function is replaced by a test
    double. When `phase_timer` is supplied, the handbook lookup is
    additionally measured as its own `ask.runtime.handbook` phase. Because
    that phase is typically nested inside a caller's own
    `ask.governance.snapshot` span, its duration is counted in both
    a known, documented limitation of `PhaseTimer.phase_total_ms()` /
    `unattributed_ms()` not being nesting-aware. The handbook lookup is a
    small fraction of the overall snapshot build, so the effect is minor.
    """
    from providence_cli.commands import _ask_backend as _backend

    root = workspace_root or _backend._resolve_workspace_root()
    if require_handshake:
        _backend._guard_handshake(root)
    last_known_fingerprint = _backend._get_last_known_fingerprint(root)
    cached_snapshot = (
        _backend._get_cached_governance_snapshot(root, last_known_fingerprint)
        if last_known_fingerprint
        else None
    )
    if cached_snapshot is not None:
        context_source = cached_snapshot["context_source"]
        fingerprint = cached_snapshot["fingerprint"]
        mandates_count = cached_snapshot["mandates_count"]
        authenticated = cached_snapshot["authenticated"]
        degraded = cached_snapshot["degraded"]
        degrade_reason = cached_snapshot["degrade_reason"]
        trust_source = cached_snapshot["trust_source"]
        governance_snapshot_to_persist = None
    else:
        (
            context_source,
            fingerprint,
            mandates_count,
            authenticated,
            degraded,
            degrade_reason,
            trust_source,
        ) = _backend._load_compiled_governance(root)
        # Only a fresh (cache-miss) load is worth persisting  re-persisting on
        # a hit would slide `computed_at` forward without ever re-verifying
        # against the real compiled state, defeating the TTL bound that keeps
        # a post-recompile cache hit self-healing (design.md D-A).
        governance_snapshot_to_persist = {
            "context_source": context_source,
            "fingerprint": fingerprint,
            "mandates_count": mandates_count,
            "authenticated": authenticated,
            "degraded": degraded,
            "degrade_reason": degrade_reason,
            "trust_source": trust_source,
        }
    if _signature_mode() == "strict" and not authenticated:
        raise PermissionError(degrade_reason)
    drift_detected = _backend._runtime_drift_check(root, fingerprint)
    root_seed_drift_detected = _backend._root_seed_drift_check(root)
    learning_signals = _collect_learning_signals(workspace_root=root)
    handbook_task_type = (
        cached_handbook_task_type
        if cached_handbook_task_type is not None
        else _infer_handbook_task_type(query, skill)
    )

    handbook_phase = (
        phase_timer.phase("ask.runtime.handbook", latency_domain="governance")
        if phase_timer is not None
        else nullcontext()
    )
    with handbook_phase:
        handbook_lookup = _cached_handbook_lookup(
            root,
            query=query,
            task_type=handbook_task_type,
            operation_phase="context_loading",
        )
    return {
        "workspace_root": root,
        "context_source": context_source,
        "fingerprint": fingerprint,
        "mandates_count": mandates_count,
        "authenticated": authenticated,
        "degraded": degraded,
        "degrade_reason": degrade_reason,
        "trust_source": trust_source,
        "drift_detected": drift_detected,
        "root_seed_drift_detected": root_seed_drift_detected,
        "learning_signals": learning_signals,
        "handbook_task_type": handbook_task_type,
        "handbook_lookup": {
            "status": handbook_lookup.status,
            "diagnostic": handbook_lookup.diagnostic,
            "matches": handbook_lookup.matches,
        },
        # Internal plumbing for the end-of-call write site (design.md D-A)
        # None on a cache hit (nothing new to persist), the fresh compiled-
        # governance fields on a miss. Never surfaced in text/JSON output;
        # downstream consumers only read known top-level fields by name.
        "_governance_snapshot_to_persist": governance_snapshot_to_persist,
    }
