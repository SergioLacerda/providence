"""PolicyEngine — runtime enforcement against compiled governance artifacts and skill policies."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..artifacts import CompiledArtifact
    from ..session import SessionState

from .._skill_contracts import SkillDefinition
from ._result import SEVERITY_HARD, SEVERITY_NONE, SEVERITY_SOFT, PolicyResult


class PolicyEngine:
    """Evaluates runtime policy outcomes from compiled governance state.

    Two entry points:
    - :meth:`evaluate` — basic has_artifact/is_sensitive check (backward-compatible).
    - :meth:`validate_preflight` — full pre-execution validation using typed objects.
    """

    def evaluate(self, *, has_artifact: bool, is_sensitive: bool) -> PolicyResult:
        """Low-level policy check.  Backward-compatible signature."""
        if not has_artifact and is_sensitive:
            return PolicyResult(
                allowed=False,
                severity=SEVERITY_HARD,
                reason="missing_governance_artifact",
                remediation="providence governance compile",
            )
        if not has_artifact:
            return PolicyResult(
                allowed=True,
                severity=SEVERITY_SOFT,
                reason="missing_governance_artifact_non_sensitive",
                remediation="providence governance compile",
            )
        return PolicyResult(allowed=True, severity=SEVERITY_NONE, reason="ok")

    def validate_preflight(
        self,
        *,
        artifact: CompiledArtifact,
        session: SessionState,
        current_profile: str,
    ) -> PolicyResult:
        """Full pre-execution policy check (§12.4 of the improvement plan).

        Enforces:
        1. Artifact exists and is non-empty.
        2. Schema version is non-empty.
        3. Session fingerprint matches artifact fingerprint.
        4. Profile consistency (master/client).
        """
        # 1. Artifact is non-empty.
        if not artifact.fingerprint:
            return PolicyResult(
                allowed=False,
                severity=SEVERITY_HARD,
                reason="artifact_missing_fingerprint",
                remediation="providence governance compile",
            )

        # 2. Schema version is present.
        if not artifact.schema_version:
            return PolicyResult(
                allowed=False,
                severity=SEVERITY_HARD,
                reason="artifact_missing_schema_version",
                remediation="providence governance compile",
            )

        # 3. Session fingerprint matches.
        if (
            session.artifact_fingerprint
            and session.artifact_fingerprint != artifact.fingerprint
        ):
            return PolicyResult(
                allowed=False,
                severity=SEVERITY_HARD,
                reason="session_fingerprint_mismatch",
                remediation="providence runtime reset-session",
            )

        # 4. Profile consistency.
        if artifact.profile and current_profile and artifact.profile != current_profile:
            return PolicyResult(
                allowed=False,
                severity=SEVERITY_HARD,
                reason="profile_mismatch",
                remediation=f"providence governance validate --profile {artifact.profile}",
            )

        return PolicyResult(allowed=True, severity=SEVERITY_NONE, reason="ok")

    def evaluate_skill_policy(
        self,
        *,
        skill_name: str,
        skill: SkillDefinition,
        enforcement_mode: str = "warn",
        project_root: Path | None = None,
    ) -> PolicyResult:
        """Evaluate skill execution policy.

        Checks:
        1. G02: Handshake guard — is skill declared in initial agreement?
        2. Risk enforcement — strict mode blocks high/critical skills.

        Args:
            skill_name: Name of the skill to evaluate.
            skill: SkillDefinition object.
            enforcement_mode: "warn", "soft", or "strict".
            project_root: Project root for handshake lookup.

        Returns:
            PolicyResult with decision (allowed/blocked).
        """
        # G02: Handshake Guard (M015) — check if skill is authorized
        handshake_result = self._check_handshake_guard(skill_name, project_root)
        if handshake_result is not None:
            return handshake_result

        # Risk-based enforcement — strict mode blocks high/critical skills
        if enforcement_mode == "strict" and skill.risk_score in {"high", "critical"}:
            return PolicyResult(
                allowed=False,
                severity=SEVERITY_HARD,
                reason=f"strict_mode blocked {skill.risk_score}-risk skill",
                remediation=f"run with --enforcement-mode=warn or manually approve '{skill_name}'",
            )

        return PolicyResult(
            allowed=True, severity=SEVERITY_NONE, reason="skill_authorized"
        )

    def _check_handshake_guard(
        self, skill_name: str, project_root: Path | None = None
    ) -> PolicyResult | None:
        """G02: Check if skill was declared in handshake (opt-in).

        Handshake guard requires explicit authorization:
        - If handshake response file exists, skill must be in skills_to_use list
        - If handshake response file does not exist, skill execution is blocked
          (unless enforcement_mode is "off" or skill risk is low)

        Returns PolicyResult if blocked, None if allowed.
        """
        try:
            root = project_root or Path.cwd()
            response_file = root / ".providence" / "runtime" / "handshake-response.json"

            if not response_file.exists():
                # Handshake not established — opt-in model requires explicit authorization
                return PolicyResult(
                    allowed=False,
                    severity=SEVERITY_HARD,
                    reason="handshake not established; skill execution requires handshake response file",
                    remediation="run 'providence governance validate' to establish a session contract first",
                )

            import json

            payload = json.loads(response_file.read_text(encoding="utf-8"))
            skills_to_use = payload.get("skills_to_use", [])
            if isinstance(skills_to_use, list) and skill_name not in skills_to_use:
                return PolicyResult(
                    allowed=False,
                    severity=SEVERITY_HARD,
                    reason=f"skill '{skill_name}' was not declared in the initial handshake",
                    remediation="update handshake to include this skill or restart with fresh handshake",
                )
        except Exception:  # nosec B110
            # JSON parse error or file read error — block execution
            return PolicyResult(
                allowed=False,
                severity=SEVERITY_HARD,
                reason="handshake response is malformed; skill execution blocked",
                remediation="delete .providence/runtime/handshake-response.json and run 'providence governance validate'",
            )

        return None
