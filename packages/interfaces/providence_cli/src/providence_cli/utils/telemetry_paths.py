"""Shared compliance telemetry path resolution."""

from __future__ import annotations

from pathlib import Path

from providence_core.governance.compliance_constants import (
    resolve_compliance_log_override,
)


def resolve_compliance_events_path(*, workspace_root: Path | None = None) -> Path:
    """Resolve compliance JSONL path with optional environment override.

    Recognizes ``SDD_COMPLIANCE_EVENTS_PATH`` (this function's own historical
    override), and also ``SDD_COMPLIANCE_LOG``/``SDD_TELEMETRY_PATH``  the
    other two env vars that resolve the same file elsewhere in the product
    via the shared `resolve_compliance_log_override`, so setting any one of
    the three is honored consistently. ``SDD_COMPLIANCE_LOG=disabled`` is not
    meaningful for this call site (there is no "no path" return here); it
    falls through to the workspace-root default like no override at all.
    """
    override = resolve_compliance_log_override()
    if override.path is not None:
        return override.path

    root = workspace_root or Path.cwd()
    return root / ".providence" / "runtime" / "compliance-events.jsonl"
