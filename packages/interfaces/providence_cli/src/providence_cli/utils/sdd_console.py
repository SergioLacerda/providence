"""Shared `[SDD] <label>  <value>` console line formatting.

Centralizes the `[SDD] ...` prefix convention already used ad hoc across
`commands/init.py`, `commands/_ask_backend/_budget.py`, and
`commands/_metrics_command_support.py`, and adds a phase/duration line
formatter for per-phase timing summaries (see
`.analysis/refined/20260730-sdd-ask-telemetry-critique/design.md` 4).
"""

from __future__ import annotations

_PHASE_LABEL_WIDTH = 28


def format_sdd_line(message: str) -> str:
    """Format a generic `[SDD] <message>` console line."""
    return f"[SDD] {message}"


def format_sdd_phase_line(label: str, duration_ms: int) -> str:
    """Format one `[SDD] <phase>  <Xs>` timing line, right-aligned duration."""
    duration_s = duration_ms / 1000.0
    return f"[SDD] {label.ljust(_PHASE_LABEL_WIDTH)}{duration_s:6.2f}s"
