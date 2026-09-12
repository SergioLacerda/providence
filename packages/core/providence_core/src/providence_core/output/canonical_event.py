"""Canonical IO types for Simple Governed IO pattern (M020).

Hierarchy:
    Governed Compact Logging
    └── Simple Governed IO
        ├── CanonicalGovernanceInput  — compact LLM input context
        ├── CanonicalLogEvent         — canonical user-facing log event
        └── ProfileRenderer           — presentation layer; never alters content
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

_MAX_LINE_LEN = 120
_MAX_OUTPUT_LINES = 3


@dataclass(frozen=True)
class CanonicalGovernanceInput:
    """Compact governance context for LLM input. Max 2 lines by default."""

    governance_state: str
    fingerprint: str
    mandates_count: int
    degraded: bool = False
    degrade_reason: str = ""

    def simple_input(self) -> str:
        """Return compact key=value governance context, max 2 lines."""
        fp = (self.fingerprint or "n/a")[:8]
        line1 = f"governance={self.governance_state} fingerprint={fp} mandates={self.mandates_count}"
        if not self.degraded:
            return line1
        reason = self.degrade_reason or "degraded"
        line2 = f"[DEGRADED: {reason} — run `providence governance compile`]"
        return f"{line1}\n{line2}"


@dataclass(frozen=True)
class CanonicalLogEvent:
    """Canonical user-facing log event. Max 3 lines in simple_output()."""

    level: str
    phase: str
    event_type: str
    summary: str = ""
    decision: str = ""
    evidence_ref: str = ""
    artifact_path: str = ""
    next_action: str = ""
    component: str = ""

    def simple_output(self) -> str:
        """Return compact event text, max 3 lines, max 120 chars per line."""
        label = f"[{self.phase}]" if self.phase else ""
        summary_text = self.summary or self.event_type
        line1 = f"{label} {self.event_type}: {summary_text}".strip()
        lines = [line1[:_MAX_LINE_LEN]]

        detail_parts: list[str] = []
        if self.decision:
            detail_parts.append(f"decision={self.decision}")
        if self.artifact_path:
            detail_parts.append(f"artifact={self.artifact_path}")
        if detail_parts:
            lines.append(("  " + " ".join(detail_parts))[:_MAX_LINE_LEN])

        if self.next_action and len(lines) < _MAX_OUTPUT_LINES:
            lines.append(f"  next={self.next_action}"[:_MAX_LINE_LEN])

        return "\n".join(lines[:_MAX_OUTPUT_LINES])

    def to_telemetry_dict(self) -> dict[str, object]:
        """Return full event dict for debug/trace structured telemetry."""
        return {k: v for k, v in asdict(self).items() if v}


@dataclass
class ProfileRenderer:
    """Presentation layer for Simple Governed IO.

    Profiles change presentation only. They MUST NOT alter decision,
    artifact_path, level, governance_state, or any canonical field value.

    debug/trace events bypass profile rendering and emit structured JSON.
    """

    profile: str = "pragmatic"

    def render(self, event: CanonicalLogEvent) -> str:
        """Render an event. debug/trace → JSON; info/warn/error → profile output."""
        if event.level in ("debug", "trace"):
            return json.dumps(event.to_telemetry_dict())
        simple = event.simple_output()
        if self.profile == "epic":
            return simple
        return simple

    def render_input(self, gov_input: CanonicalGovernanceInput) -> str:
        """Render governance input context. Profile is presentation-only."""
        return gov_input.simple_input()
