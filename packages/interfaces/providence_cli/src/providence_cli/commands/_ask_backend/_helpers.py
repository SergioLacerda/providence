"""Internal helpers for the ``providence ask`` command pipeline."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
from typer.models import OptionInfo

from providence_cli.services.ask_context import (
    get_profile_state as _get_profile_state_impl,
)
from providence_cli.services.ask_context import (
    load_compiled_governance as _load_compiled_governance,
)
from providence_cli.services.ask_context import (
    resolve_workspace_root as _resolve_workspace_root,
)
from providence_cli.services.ask_context_drift import (
    check_fingerprint_drift as _check_fingerprint_drift,
)
from providence_cli.services.ask_context_drift import (
    check_root_seed_drift as _check_root_seed_drift,
)
from providence_cli.services.ask_context_drift import (
    get_last_known_fingerprint as _get_last_known_fingerprint,
)
from providence_cli.services.ask_context_drift import (
    write_runtime_cache as _write_runtime_cache,
)
from providence_cli.services.ask_context_routing import (
    resolve_routing_decision as _resolve_routing_decision,
)
from providence_cli.services.ask_context_routing import (
    store_routing_decision as _store_routing_decision,
)
from providence_cli.services.ask_context_routing import (
    write_runtime_cache_and_routing_decision as _write_runtime_cache_and_routing_decision,
)
from providence_cli.services.ask_context_snapshot import (
    get_cached_governance_snapshot as _get_cached_governance_snapshot,
)
from providence_cli.services.ask_governance import (
    signature_mode as _signature_mode_impl,
)
from providence_cli.services.ask_governance import (
    try_sdd_compiled_dir as _try_sdd_compiled_dir_impl,
)
from providence_cli.services.ask_hash import _hash_query
from providence_cli.services.ask_renderer import (
    render_context_header as _render_context_header,
)
from providence_cli.services.ask_renderer import (
    render_governance_footer as _render_governance_footer_impl,
)
from providence_cli.shared.constants import TRUE_VALUES as _TRUE_VALUES

__all__ = [
    "_check_fingerprint_drift",
    "_get_cached_governance_snapshot",
    "_get_last_known_fingerprint",
    "_hash_query",
    "_load_compiled_governance",
    "_resolve_routing_decision",
    "_resolve_workspace_root",
    "_store_routing_decision",
    "_write_runtime_cache",
    "_write_runtime_cache_and_routing_decision",
]

logger = logging.getLogger(__name__)


def _now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def _normalize_typer_value(value: Any, default: Any) -> Any:
    """Normalize Typer OptionInfo leakage when command functions are called directly."""
    return default if isinstance(value, OptionInfo) else value


def _prefer_full_summary() -> bool:
    """Return whether ask context rendering should prefer summary_full."""
    raw = os.environ.get("SDD_ASK_PREFER_FULL_SUMMARY", "")
    return raw.strip().lower() in _TRUE_VALUES


def _try_sdd_compiled_dir(sdd_compiled: Path) -> tuple[str, str, int] | None:
    return _try_sdd_compiled_dir_impl(sdd_compiled, logger=logger)


def _signature_mode() -> str:
    return _signature_mode_impl()


def _get_cached_ahp() -> dict[str, Any] | None:
    ctx = click.get_current_context(silent=True)
    if ctx is not None and isinstance(ctx.obj, dict):
        cached = ctx.obj.get("_ahp")
        if isinstance(cached, dict):
            return cached
    return None


def _get_profile_state() -> tuple[str, str]:
    """Return (profile, state) best-effort; never raises."""
    from providence_cli.commands import _ask_backend as _backend

    return _get_profile_state_impl(_backend._resolve_workspace_root())


def _runtime_drift_check(workspace_root: Path, loaded_fingerprint: str) -> bool:
    return _check_fingerprint_drift(workspace_root, loaded_fingerprint)


def _root_seed_drift_check(workspace_root: Path) -> bool:
    return _check_root_seed_drift(workspace_root)


def _resolve_ask_drift_type(*, drift_detected: bool, authenticated: bool) -> str:
    """Classify ask drift for telemetry consumers."""
    if not drift_detected:
        return "none"
    if not authenticated:
        return "auth_drift"
    return "fingerprint_drift"


def _resolve_ask_degraded_reason(
    *, degraded: bool, degrade_reason: str, authenticated: bool
) -> str:
    """Provide stable degraded reason when none is explicitly available."""
    if degrade_reason.strip():
        return degrade_reason.strip()
    if degraded and not authenticated:
        return "artifact_unverified"
    if degraded:
        return "degraded_unspecified"
    return ""


def _render_context_output(
    fingerprint: str,
    mandates_count: int,
    *,
    degraded: bool,
    degrade_reason: str,
) -> str:
    return _render_context_header(
        fingerprint,
        mandates_count,
        degraded=degraded,
        degrade_reason=degrade_reason,
    )


def _governance_footer_for_state(
    *,
    state: str,
    profile: str,
    drift_detected: bool,
    root_seed_drift_detected: bool | None = None,
) -> str:
    return _render_governance_footer_impl(
        state=state,
        profile=profile,
        drift_detected=drift_detected,
        root_seed_drift_detected=root_seed_drift_detected,
    )
