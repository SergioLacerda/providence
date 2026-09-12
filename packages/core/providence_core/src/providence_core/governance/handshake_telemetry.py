"""Handshake Telemetry - Non-blocking governance event emission.

Emits governance-checked events to providence_runtime.telemetry.
"""

import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


class HandshakeTelemetry:
    """Emit non-blocking governance telemetry events."""

    def emit(
        self,
        agent_id: str,
        final_state: str,
        confidence: float,
        project_root: Path,
        gap_status: str,
        skill_profile: str,
        spec_fingerprint: str,
        mandates_loaded: list[str] | None = None,
    ) -> None:
        """Emit governance.checked telemetry event. Failure is non-blocking.

        Args:
            agent_id: Identifier for the agent
            final_state: Final handshake state
            confidence: Confidence score (0-1)
            project_root: Root directory of the project
            gap_status: GAP status
            skill_profile: Current skill profile
            spec_fingerprint: Governance spec fingerprint
            mandates_loaded: List of active mandates
        """
        try:
            from providence_runtime.telemetry import RuntimeEvent, TelemetrySink

            # Determine context_source from canonical .providence governance artifact
            gov_path = (
                project_root / ".providence" / "compiled" / "governance-core.json"
            )
            context_source = "json" if gov_path.exists() else "none"

            sink = TelemetrySink()
            sink.emit(
                RuntimeEvent(
                    event="governance.checked",
                    command="governance",
                    status="ok",
                    trace_id=str(uuid.uuid4()),
                    agent_id=agent_id,
                    details={
                        "profile": gap_status.lower() or "unknown",
                        "skill_profile": skill_profile,
                        "state": final_state,
                        "context_source": context_source,
                        "compiled_fingerprint_used": (
                            spec_fingerprint[:16] if spec_fingerprint else ""
                        ),
                        "mandates_loaded": len(mandates_loaded or []),
                        "confidence": round(confidence, 1),
                    },
                )
            )
            sink.flush()
        except Exception:
            logger.debug("Failed to emit governance checked event", exc_info=True)
