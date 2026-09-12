"""Handshake Protocol Data Models (M015).

Dataclasses for challenge and response in the bidirectional handshake.
"""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class HandshakeRequest:
    """Formal challenge sent to the agent to initiate the handshake (M015)."""

    protocol_version: str = "1.0"
    agent_id: str = ""
    session_id: str = ""
    challenge_id: str = ""
    timestamp: str = ""
    task: dict[str, str] = field(default_factory=dict)
    available_skills: list[dict[str, Any]] = field(default_factory=list)
    active_mandates: list[str] = field(default_factory=list)
    budget: dict[str, Any] = field(default_factory=dict)
    signature_status: str = "unavailable"
    governance_fingerprint: str = ""
    requires_structured_response: bool = True

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return asdict(self)


@dataclass
class HandshakeReport:
    """Complete handshake validation report."""

    state: str  # NOT_CONNECTED | MISCONFIGURED | NOT_INITIALIZED | PARTIAL | HEALTHY
    confidence: float  # 0-100%
    checks: list[dict[str, Any]]
    actions: list[str]
    cached: bool
    cache_age_seconds: int | None


@dataclass
class HandshakeResponse:
    """Formal agent response to a handshake request (M015).

    ``challenge_id``, ``session_id``, ``governance_fingerprint``,
    ``issued_at`` and ``expires_at`` bind this response to the specific
    challenge it answers (SEC-01/SEC-03) — they are stamped server-side by
    ``HandshakeChallenge.complete_handshake`` from the persisted challenge
    state, never trusted from caller-supplied ``response_data``, so a
    response cannot be forged to claim a binding it wasn't actually issued.
    """

    agent_id: str
    understood_mandates: list[str]
    skills_to_use: list[str]
    acknowledged_signature: bool
    plan_summary: str = ""
    compliance_declaration: bool = True
    timestamp: str = ""
    challenge_id: str = ""
    session_id: str = ""
    governance_fingerprint: str = ""
    issued_at: str = ""
    expires_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HandshakeResponse":
        """From Dict."""
        return cls(
            agent_id=data.get("agent_id", "unknown"),
            understood_mandates=data.get("understood_mandates", []),
            skills_to_use=data.get("skills_to_use", []),
            acknowledged_signature=bool(data.get("acknowledged_signature", False)),
            plan_summary=data.get("plan_summary", ""),
            compliance_declaration=bool(data.get("compliance_declaration", True)),
            timestamp=data.get("timestamp", ""),
            challenge_id=data.get("challenge_id", ""),
            session_id=data.get("session_id", ""),
            governance_fingerprint=data.get("governance_fingerprint", ""),
            issued_at=data.get("issued_at", ""),
            expires_at=data.get("expires_at", ""),
        )
