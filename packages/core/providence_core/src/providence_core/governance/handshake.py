"""Agent Handshake Protocol facade."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from ._handshake_constants import ACTIONS, STATES
from ._handshake_support import (
    cached_report,
    find_project_root,
    fresh_validation,
    resolve_cache_ttl,
)
from ._handshake_validation_result import ValidationResult
from .handshake_cache import HandshakeCache
from .handshake_challenge import HandshakeChallenge
from .handshake_formatter import HandshakeFormatter
from .handshake_models import HandshakeReport, HandshakeRequest, HandshakeResponse
from .handshake_telemetry import HandshakeTelemetry
from .handshake_validator import GovernanceValidator
from .semantic_trigger import SemanticTrigger

__all__ = [
    "AgentHandshakeProtocol",
    "HandshakeRequest",
    "ValidationResult",
    "HandshakeReport",
    "HandshakeResponse",
]


class AgentHandshakeProtocol:
    """Facade for the multi-layer governance handshake workflow."""

    STATES = STATES
    ACTIONS = ACTIONS

    def __init__(
        self, project_root: Path | None = None, cache_ttl_minutes: int | None = None
    ):
        self.project_root = find_project_root(project_root)
        self.cache_dir = self.project_root / ".providence" / "runtime"
        self.cache_file = self.cache_dir / "governance-state.json"
        self.response_file = self.cache_dir / "handshake-response.json"
        self.cache_ttl = resolve_cache_ttl(
            self.project_root, self.cache_file, self.cache_dir, cache_ttl_minutes
        )
        self.validation_results: list[dict[str, Any]] = []
        self.current_state = "NOT_CONNECTED"
        self.current_confidence = 0.0
        self.gap_status = "NOT_ACTIVE"
        self.agent_id = os.environ.get("SDD_AGENT_ID", "unknown")
        self.spec_fingerprint = ""
        self.mandates_loaded: list[str] = []
        self.skill_profile = "default"
        self._validator = GovernanceValidator(self.project_root)
        self._cache = HandshakeCache(
            self.cache_file,
            self.cache_dir,
            self.cache_ttl,
            self.project_root,
            self.agent_id,
        )
        self._formatter = HandshakeFormatter()
        self._trigger = SemanticTrigger()
        self._challenge = HandshakeChallenge(
            self.agent_id, self.project_root, self.cache_dir, self.response_file
        )
        self._telemetry = HandshakeTelemetry()

    def should_run_handshake(self, user_input: str) -> bool:
        """Return whether input should trigger handshake evaluation."""
        return self._trigger.should_run_handshake(user_input)

    def _layer_1_discovery(self) -> tuple[str, list[ValidationResult]]:
        return self._validator.layer_1_discovery()

    def _layer_2_link_validation(self) -> tuple[str, list[ValidationResult]]:
        return self._validator.layer_2_link_validation()

    def _layer_3_runtime_validation(self) -> tuple[str, list[ValidationResult]]:
        return self._validator.layer_3_runtime_validation()

    def _layer_4_governance_health(self) -> tuple[str, list[ValidationResult]]:
        return self._validator.layer_4_governance_health()

    def _compute_final_state(self, l1: str, l2: str, l3: str, l4: str) -> str:
        return self._validator.compute_final_state(l1, l2, l3, l4)

    def _compute_confidence(self, all_results: list[ValidationResult]) -> float:
        return self._validator.compute_confidence(all_results)

    def _load_cache(self) -> dict[str, Any] | None:
        return self._cache.load_cache()

    def _extract_governance_core(self) -> dict[str, Any] | None:
        return self._cache.extract_governance_core()

    def _extract_mandates(self) -> list[str]:
        return self._cache.extract_mandates()

    def _compute_spec_fingerprint(self) -> str:
        return self._cache.compute_spec_fingerprint()

    def _map_ahp_to_gap(self, ahp_state: str, confidence: float) -> str:
        return self._cache.map_ahp_to_gap(ahp_state, confidence)

    def _save_cache(
        self, state: str, checks: list[dict[str, Any]], confidence: float
    ) -> None:
        self.skill_profile = self._cache.extract_skill_profile()
        self._cache.save_cache(state, checks, confidence, self.skill_profile)
        self.mandates_loaded = self._cache.mandates_loaded
        self.spec_fingerprint = self._cache.spec_fingerprint
        self.gap_status = self._cache.gap_status

    def _emit_governance_event(self, final_state: str, confidence: float) -> None:
        self._telemetry.emit(
            self.agent_id,
            final_state,
            confidence,
            self.project_root,
            self.gap_status,
            self.skill_profile,
            self.spec_fingerprint,
            self.mandates_loaded,
        )

    def format_gap_output(
        self, mode: Literal["silent", "compact", "verbose"] = "compact"
    ) -> str:
        """Format the current governance gap summary."""
        self._formatter.gap_status = self.gap_status
        self._formatter.mandates_loaded = self.mandates_loaded
        self._formatter.current_confidence = self.current_confidence
        return self._formatter.format_gap_output(mode=mode)

    def format_combined_output(
        self,
        state: str,
        report: HandshakeReport,
        mode: Literal["silent", "compact", "verbose"] = "compact",
    ) -> str:
        """Format combined handshake and governance-gap output."""
        self._formatter.gap_status = self.gap_status
        self._formatter.mandates_loaded = self.mandates_loaded
        self._formatter.current_confidence = self.current_confidence
        return self._formatter.format_combined_output(state, report, mode=mode)

    def validate(
        self,
        output_mode: Literal["silent", "compact", "verbose"] = "compact",
        force_recheck: bool = False,
    ) -> tuple[str, HandshakeReport]:
        """Validate governance state, using cache unless recheck is forced."""
        if not force_recheck:
            cache = self._load_cache()
            if (
                cache
                and cache.get("state") == "NOT_CONNECTED"
                and (self.project_root / ".providence").is_dir()
            ):
                cache = None
            if cache:
                return cached_report(self, cache)
        return fresh_validation(self)

    def complete_handshake(self, response_data: dict[str, Any]) -> HandshakeResponse:
        """Persist and validate the provided handshake response payload."""
        return self._challenge.complete_handshake(response_data)

    def generate_challenge(
        self, task_description: str = "General Task", task_type: str = "other"
    ) -> HandshakeRequest:
        """Create a new handshake challenge for the current task."""
        return self._challenge.generate_challenge(
            task_description,
            task_type,
            self.mandates_loaded or self._extract_mandates(),
        )

    def get_handshake_response(self) -> HandshakeResponse | None:
        """Return the persisted handshake response when available."""
        return self._challenge.get_handshake_response()

    def is_handshake_valid(self, strict: bool = False) -> bool:
        """Check whether the stored handshake response is still valid."""
        return self._challenge.is_handshake_valid(strict)

    def format_output(
        self,
        state: str,
        report: HandshakeReport,
        mode: Literal["silent", "compact", "verbose"] = "compact",
    ) -> str:
        """Format the primary handshake report."""
        return self._formatter.format_output(state, report, mode=mode)
