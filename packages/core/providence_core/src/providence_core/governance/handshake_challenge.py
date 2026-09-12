"""Handshake Challenge - M015 bidirectional challenge/response protocol.

Manages the formal challenge and response lifecycle for agent handshakes.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from providence_core.governance.handshake_models import (
    HandshakeRequest,
    HandshakeResponse,
)

logger = logging.getLogger(__name__)

# Authorization expiration, independent of HandshakeCache's governance-health
# cache TTL (`_TTL_CLIENT_MINUTES`/`_TTL_MASTER_MINUTES` in handshake_cache.py)
# — see SEC-03: the health-cache TTL was being conflated with authorization
# expiration, which are different concerns.
_AUTHORIZATION_TTL_MINUTES = 60


class HandshakeChallenge:
    """M015 protocol: bidirectional challenge/response lifecycle."""

    def __init__(
        self, agent_id: str, project_root: Path, cache_dir: Path, response_file: Path
    ):
        """Initialize challenge/response handler.

        Args:
            agent_id: Identifier for the agent
            project_root: Root directory of the project
            cache_dir: Directory for handshake cache
            response_file: Path to store handshake response
        """
        self.agent_id = agent_id
        self.project_root = project_root
        self.cache_dir = cache_dir
        self.response_file = response_file
        self.challenge_state_file = cache_dir / "handshake-challenge.json"

    def _resolve_signature_status(self) -> str:
        """Resolve signature status for the canonical governance artifact.

        Distinguishes presence of a `.sig` file from actual cryptographic
        verification — a `.sig` file existing next to the artifact does not
        by itself prove the artifact is authentic (it could be stale,
        tampered with, or signed by an untrusted key). Reuses
        `providence_runtime.signatures.validate_artifact_signature`, the same
        Ed25519 + trusted-keyring check used elsewhere, instead of
        re-deriving a presence-only heuristic. See
        `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` SEC-05.

        Returns one of: "unavailable" (signature mode is off), "unsigned"
        (no `.sig` file), "verified" (crypto check passed), or the
        validator's own failure `code` (e.g. "SIG_INVALID",
        "SIG_UNTRUSTED_KEY", "SIG_PAYLOAD_HASH_MISMATCH") on failure.
        """
        signature_mode = os.environ.get("SDD_SIGNATURE_MODE", "off").strip().lower()
        if signature_mode not in {"warn", "strict"}:
            return "unavailable"

        gov_path = (
            self.project_root / ".providence" / "compiled" / "governance-core.json"
        )
        if not gov_path.exists():
            return "unsigned"
        sig_path = gov_path.with_suffix(gov_path.suffix + ".sig")
        if not sig_path.exists():
            return "unsigned"

        from providence_runtime.signatures import validate_artifact_signature

        result = validate_artifact_signature(
            artifact_path=gov_path,
            sig_path=sig_path,
            strict=signature_mode == "strict",
            workspace_root=self.project_root,
        )
        return "verified" if result.ok else result.code

    def _compute_governance_fingerprint(self) -> str:
        """Compute the current governance-version fingerprint.

        Reuses `HandshakeCache.compute_spec_fingerprint()` (already the
        canonical way this codebase hashes the compiled governance-core
        artifact) instead of re-deriving a second hashing scheme.
        """
        from providence_core.governance.handshake_cache import HandshakeCache

        cache = HandshakeCache(
            cache_file=self.cache_dir / "governance-state.json",
            cache_dir=self.cache_dir,
            cache_ttl=timedelta(minutes=_AUTHORIZATION_TTL_MINUTES),
            project_root=self.project_root,
            agent_id=self.agent_id,
        )
        return cache.compute_spec_fingerprint()

    def _resolve_budget(self) -> dict[str, Any]:
        """Resolve the challenge's declared token/USD budget.

        There is no live, queryable budget-tracker instance available at
        challenge-generation time (`providence_runtime.budget.TokenBudget` is
        instantiated per-consumer with in-memory consumption state, not a
        workspace-wide singleton this module can read). Rather than present
        a fabricated ceiling as if it were a real computed limit (the SEC-06
        bug), this reads an optional configured ceiling from
        `pyproject.toml`'s `[tool.providence.runtime]` table — the same extension
        point `HandshakeCache.resolve_ttl_minutes()` already uses for
        `handshake_ttl_minutes` — and otherwise reports "unknown" explicitly.
        See `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`
        SEC-06.
        """
        max_tokens: int | str = "unknown"
        max_cost_usd: float | str = "unknown"
        try:
            pyproject_path = self.project_root / "pyproject.toml"
            if pyproject_path.exists():
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib
                config = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
                runtime_cfg = config.get("tool", {}).get("sdd", {}).get("runtime", {})
                if "max_tokens_per_session" in runtime_cfg:
                    max_tokens = int(runtime_cfg["max_tokens_per_session"])
                if "max_cost_usd_per_session" in runtime_cfg:
                    max_cost_usd = float(runtime_cfg["max_cost_usd_per_session"])
        except (OSError, ValueError, KeyError, TypeError, ImportError):
            logger.debug(
                "Could not parse session budget from pyproject.toml", exc_info=True
            )
        return {"remaining_tokens": max_tokens, "remaining_usd": max_cost_usd}

    def _load_challenge_state(self) -> dict[str, Any] | None:
        """Load the most recently issued challenge's server-side state.

        Returns None when no challenge was ever issued for this workspace
        (legacy/back-compat path — see `is_handshake_valid`).
        """
        if not self.challenge_state_file.exists():
            return None
        try:
            data = json.loads(self.challenge_state_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except Exception as exc:
            logger.debug("Failed to load handshake challenge state: %s", exc)
            return None

    def generate_challenge(
        self,
        task_description: str = "General Task",
        task_type: str = "other",
        mandates_loaded: list[str] | None = None,
    ) -> HandshakeRequest:
        """Generate a formal Handshake Request challenge (M015).

        This challenge contains the necessary context for an agent to form
        a valid handshake response, including available skills and mandates.

        Args:
            task_description: Description of the task
            task_type: Type of task
            mandates_loaded: List of active mandates

        Returns:
            HandshakeRequest with challenge details
        """
        # 1. Resolve skills
        try:
            from providence_runtime.skills import SkillEngine

            engine = SkillEngine()
            # Export in JSON format to be included in challenge
            skills_payload = engine.export_skills_payload(fmt="json")
            available_skills = skills_payload.get("skills", [])
        except Exception:  # nosec B110
            available_skills = []

        # 2. Resolve mandates
        active_mandates = mandates_loaded or []

        # 3. Resolve signature status
        signature_status = self._resolve_signature_status()

        # 4. Resolve budget
        budget = self._resolve_budget()

        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        challenge_id = f"chal_{uuid.uuid4().hex[:12]}"
        governance_fingerprint = self._compute_governance_fingerprint()
        issued_at = datetime.now().isoformat()

        request = HandshakeRequest(
            session_id=session_id,
            challenge_id=challenge_id,
            timestamp=issued_at,
            task={"description": task_description, "type": task_type},
            available_skills=available_skills,
            active_mandates=active_mandates,
            budget=budget,
            signature_status=signature_status,
            governance_fingerprint=governance_fingerprint,
        )

        # Persist server-side challenge state so a later, separate process
        # (e.g. `providence governance handshake --response`) can bind the eventual
        # response to exactly this challenge — see SEC-01/SEC-02/SEC-03.
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.challenge_state_file.write_text(
                json.dumps(
                    {
                        "challenge_id": challenge_id,
                        "session_id": session_id,
                        "governance_fingerprint": governance_fingerprint,
                        "signature_status": signature_status,
                        "required_mandates": active_mandates,
                        "issued_at": issued_at,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to persist handshake challenge state: %s", exc)

        return request

    def complete_handshake(self, response_data: dict[str, Any]) -> HandshakeResponse:
        """Finalize the bidirectional handshake by recording the agent's response.

        Validates that the agent has acknowledged signatures and declared skills.

        Binding fields (``challenge_id``, ``session_id``,
        ``governance_fingerprint``, ``issued_at``, ``expires_at``) are always
        stamped here from the server-side persisted challenge state, never
        taken from caller-supplied ``response_data`` — a response cannot
        forge a binding to a challenge it did not actually receive (SEC-01).
        When no challenge was ever issued (legacy callers, or a response
        supplied out-of-band), the binding fields are left empty and
        `is_handshake_valid` falls back to its pre-SEC-01 behavior.

        Args:
            response_data: Dictionary containing the agent's response

        Returns:
            HandshakeResponse object
        """
        response = HandshakeResponse.from_dict(response_data)
        if not response.timestamp:
            response.timestamp = datetime.now().isoformat()

        challenge_state = self._load_challenge_state()
        if challenge_state is not None:
            response.challenge_id = str(challenge_state.get("challenge_id", ""))
            response.session_id = str(challenge_state.get("session_id", ""))
            response.governance_fingerprint = str(
                challenge_state.get("governance_fingerprint", "")
            )
            issued_at = str(challenge_state.get("issued_at", ""))
            response.issued_at = issued_at
            try:
                response.expires_at = (
                    datetime.fromisoformat(issued_at)
                    + timedelta(minutes=_AUTHORIZATION_TTL_MINUTES)
                ).isoformat()
            except ValueError:
                response.expires_at = ""

        # Persist response. Written to a temp file and atomically renamed
        # into place so a concurrent reader never observes a partially
        # written file (SEC-04) — full per-session response isolation is
        # deliberately out of scope: the protocol persists one declarative
        # response per workspace by design, and cross-session authorization
        # reuse is prevented by the challenge_id/governance_fingerprint
        # binding above, not by file-per-session isolation.
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            tmp_file = self.response_file.with_suffix(
                self.response_file.suffix + f".tmp-{os.getpid()}"
            )
            tmp_file.write_text(
                json.dumps(response.to_dict(), indent=2), encoding="utf-8"
            )
            os.replace(tmp_file, self.response_file)
            logger.info("Handshake response completed for agent: %s", response.agent_id)
        except Exception as exc:
            logger.error("Failed to persist handshake response: %s", exc)

        return response

    def get_handshake_response(self) -> HandshakeResponse | None:
        """Retrieve the currently active handshake response.

        Returns:
            HandshakeResponse if file exists and is valid, None otherwise
        """
        if not self.response_file.exists():
            return None
        try:
            data = json.loads(self.response_file.read_text(encoding="utf-8"))
            return HandshakeResponse.from_dict(data)
        except Exception:
            return None

    def is_handshake_valid(self, strict: bool = False) -> bool:
        """Check if a valid handshake exists and meets security requirements.

        Beyond mere presence, this now confronts the response against the
        server-side challenge state it should have answered (SEC-01/SEC-02):

        - challenge_id/session_id must match the most recently issued
          challenge for this workspace (rejects a response replayed from a
          different session or challenge).
        - governance_fingerprint must still match the *current* governance
          state, re-derived live — not only the value recorded at issuance
          — so a governance change after completion invalidates the
          response (SEC-03).
        - every mandate recorded as required at issuance must appear in
          ``understood_mandates`` (rejects incomplete adherence).
        - the response must not be past its ``expires_at`` (SEC-03).
        - in strict mode, ``acknowledged_signature=True`` alone is no longer
          sufficient — the challenge's own independently-verified
          ``signature_status`` (SEC-05's real crypto check) must also read
          "verified" (SEC-02's "acknowledged_signature does not substitute
          cryptographic verification").

        When no challenge was ever issued for this workspace (no
        `handshake-challenge.json`), falls back to the pre-SEC-01 behavior
        (presence + optional strict acknowledgement) for backward
        compatibility with responses supplied out-of-band.

        Args:
            strict: If True, require acknowledged_signature AND a
                cryptographically verified signature status.

        Returns:
            True if handshake is valid, False otherwise
        """
        response = self.get_handshake_response()
        if response is None:
            return False
        if strict and not response.acknowledged_signature:
            return False

        challenge_state = self._load_challenge_state()
        if challenge_state is None:
            return True

        return self._binding_is_valid(response, challenge_state, strict)

    def _binding_is_valid(
        self,
        response: HandshakeResponse,
        challenge_state: dict[str, Any],
        strict: bool,
    ) -> bool:
        """Confront *response* against the challenge it should have answered.

        Split out of `is_handshake_valid` purely to keep both functions
        under the project's cyclomatic-complexity threshold — see that
        method's docstring for what each check means (SEC-01/SEC-02/SEC-03).
        """
        if response.challenge_id != challenge_state.get("challenge_id"):
            return False
        if response.session_id != challenge_state.get("session_id"):
            return False
        if response.governance_fingerprint != self._compute_governance_fingerprint():
            return False

        required_mandates = challenge_state.get("required_mandates") or []
        if not set(required_mandates) <= set(response.understood_mandates):
            return False

        if response.expires_at:
            try:
                if datetime.now() > datetime.fromisoformat(response.expires_at):
                    return False
            except ValueError:
                return False

        return not (strict and challenge_state.get("signature_status") != "verified")
