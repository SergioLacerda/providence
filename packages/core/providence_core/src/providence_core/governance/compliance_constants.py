"""Compliance event type constants and utilities."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Event type constants
COMMAND_INVOKED = "COMMAND_INVOKED"
GOVERNANCE_CHECKED = "GOVERNANCE_CHECKED"
WORKSPACE_INIT = "WORKSPACE_INIT"
COMPILE_COMPLETE = "COMPILE_COMPLETE"
VIOLATION = "VIOLATION"
ASK_COMMAND = "ASK_COMMAND"
ASK_FULL_COMMAND = "ASK_FULL_COMMAND"

_COMPLIANCE_LOG_DISABLED = "disabled"

# Historically three independent env vars — SDD_COMPLIANCE_LOG (governance
# internals), SDD_COMPLIANCE_EVENTS_PATH (providence ask telemetry), SDD_TELEMETRY_PATH
# (providence telemetry/providence audit commands) — each read by its own call site with no
# shared implementation, so setting only one of them left the others silently
# pointing at the default location. All three now resolve through this single
# precedence list; first one set wins. SDD_COMPLIANCE_LOG keeps top precedence
# because it is the only one with the `disabled` sentinel.
_COMPLIANCE_PATH_ENV_VARS: tuple[str, ...] = (
    "SDD_COMPLIANCE_LOG",
    "SDD_COMPLIANCE_EVENTS_PATH",
    "SDD_TELEMETRY_PATH",
)


@dataclass(frozen=True)
class ComplianceLogOverride:
    """Result of checking the compliance-events env var overrides.

    `path` is set only when an override was found and it is not the
    `disabled` sentinel. `diverged_vars` lists every *other* set var whose
    resolved path differs from the winning one — empty when zero or one var
    is set, or when all set vars agree.
    """

    disabled: bool
    path: Path | None
    winner_var: str | None = None
    diverged_vars: dict[str, Path] = field(default_factory=dict)


def _resolve_override_value(raw: str) -> Path:
    candidate = Path(raw).expanduser()
    return candidate if candidate.is_absolute() else (Path.cwd() / candidate).resolve()


def resolve_compliance_log_override() -> ComplianceLogOverride:
    """Check all three compliance-events env vars, in precedence order.

    Every caller that resolves the compliance/telemetry-events JSONL path
    should go through this instead of reading its own single env var, so a
    value set on any of the three is honored consistently everywhere.
    """
    raw_values = {
        name: raw
        for name in _COMPLIANCE_PATH_ENV_VARS
        if (raw := os.environ.get(name, "").strip())
    }
    if not raw_values:
        return ComplianceLogOverride(disabled=False, path=None)

    winner_name = next(name for name in _COMPLIANCE_PATH_ENV_VARS if name in raw_values)
    winner_raw = raw_values[winner_name]

    if (
        winner_name == "SDD_COMPLIANCE_LOG"
        and winner_raw.lower() == _COMPLIANCE_LOG_DISABLED
    ):
        # Top precedence and an explicit, unambiguous intent — disabled wins
        # regardless of what any lower-precedence var says.
        return ComplianceLogOverride(disabled=True, path=None, winner_var=winner_name)

    resolved = {name: _resolve_override_value(raw) for name, raw in raw_values.items()}
    winner_path = resolved[winner_name]
    diverged = {
        name: path
        for name, path in resolved.items()
        if name != winner_name and path != winner_path
    }
    return ComplianceLogOverride(
        disabled=False, path=winner_path, winner_var=winner_name, diverged_vars=diverged
    )


def default_log_path(workspace_root: Path | None = None) -> Path | None:
    """Resolve JSONL path, respecting the compliance-events env var overrides.

    Returns None when SDD_COMPLIANCE_LOG=disabled, which suppresses all writes.
    Set SDD_COMPLIANCE_LOG=/path/to/file.jsonl to override the default location.
    """
    override = resolve_compliance_log_override()
    if override.disabled:
        return None
    if override.path is not None:
        if override.diverged_vars:
            logger.warning(
                "Compliance-events path env vars disagree — using %s=%s; "
                "ignoring conflicting override(s): %s",
                override.winner_var,
                override.path,
                {k: str(v) for k, v in override.diverged_vars.items()},
            )
        return override.path

    root = workspace_root
    if root is None:
        try:
            from providence_core.utils.environment import find_workspace_root

            root = find_workspace_root()
        except Exception as exc:
            logger.debug(
                "Could not resolve workspace root for compliance log path: %s", exc
            )
    if root is None:
        root = Path.cwd()
    return root / ".providence" / "runtime" / "compliance-events.jsonl"
