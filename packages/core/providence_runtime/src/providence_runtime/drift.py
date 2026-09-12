"""Drift detection — classify and surface governance state mismatches."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .artifacts import CompiledArtifact
    from .session import SessionState

# Canonical drift taxonomy (§12.5 of the improvement plan).
DRIFT_NONE = "none"
DRIFT_SPEC = "spec_drift"  # source changed, artifact not recompiled
DRIFT_PROFILE = "profile_drift"  # runtime profile ≠ expected (master/client mismatch)
DRIFT_SESSION = "session_drift"  # cached session bound to a stale artifact fingerprint
DRIFT_POLICY = "policy_drift"  # policy-set version mismatch
DRIFT_MISSING = "missing_fingerprint"
DRIFT_MISMATCH = "fingerprint_mismatch"
DRIFT_BOOTSTRAP = "bootstrap_drift"  # root seed fingerprint ≠ metadata.json

# Deterministic remediation commands per drift type.
_REMEDIATION: dict[str, str] = {
    DRIFT_NONE: "",
    DRIFT_SPEC: "providence governance compile",
    DRIFT_PROFILE: "providence governance validate --profile <expected>",
    DRIFT_SESSION: "providence runtime reset-session",
    DRIFT_POLICY: "providence governance compile --force",
    DRIFT_MISSING: "providence governance compile",
    DRIFT_MISMATCH: "providence governance compile",
    DRIFT_BOOTSTRAP: "providence install --wizard",
}

# Matches the generated header comment root seeds carry, e.g.:
# "# Governance fingerprint: 58a087b3c9fb9ce2"
_SEED_FINGERPRINT_RE = re.compile(
    r"Governance fingerprint:\s*([0-9a-fA-F]+)", re.IGNORECASE
)


def extract_seed_fingerprint(seed_content: str) -> str | None:
    """Extract the `Governance fingerprint: <hash>` comment from a root seed file.

    Returns None when the seed has no such header — callers treat that as "cannot
    verify" rather than "drifted", since not every seed surface embeds a fingerprint.
    """
    match = _SEED_FINGERPRINT_RE.search(seed_content)
    return match.group(1) if match else None


def check_root_seed_drift(
    *, seed_name: str, seed_content: str, metadata_fingerprint: str | None
) -> DriftReport:
    """Compare a root seed's embedded fingerprint against metadata.json's canonical one.

    `metadata_fingerprint` is the workspace's `.providence/metadata.json` → `governance_fingerprint`
    top-level field (see the Metadata Contract this check enforces). A seed with no
    embedded fingerprint comment, or a workspace with no canonical fingerprint yet, is
    reported as `DRIFT_MISSING` (cannot verify) rather than silently treated as clean.
    """
    seed_fingerprint = extract_seed_fingerprint(seed_content)
    if not seed_fingerprint or not metadata_fingerprint:
        return DriftReport(
            drift_detected=True,
            drift_type=DRIFT_MISSING,
            remediation_command=_REMEDIATION[DRIFT_MISSING],
            details=(
                f"Could not verify {seed_name}: seed_fingerprint="
                f"{seed_fingerprint!r} metadata_fingerprint={metadata_fingerprint!r}."
            ),
        )
    if seed_fingerprint != metadata_fingerprint:
        return DriftReport(
            drift_detected=True,
            drift_type=DRIFT_BOOTSTRAP,
            remediation_command=_REMEDIATION[DRIFT_BOOTSTRAP],
            details=(
                f"{seed_name} fingerprint '{seed_fingerprint}' does not match "
                f".providence/metadata.json governance_fingerprint '{metadata_fingerprint}'."
            ),
        )
    return DriftReport(drift_detected=False, drift_type=DRIFT_NONE)


@dataclass
class DriftReport:
    """Result of a drift detection operation."""

    drift_detected: bool
    drift_type: str
    remediation_command: str = ""
    details: str = ""

    @property
    def is_clean(self) -> bool:
        """Is Clean."""
        return not self.drift_detected


class DriftDetector:
    """Detects runtime drift between session state and compiled artifact.

    Two entry points:
    - :meth:`detect` — low-level fingerprint comparison (backward-compatible).
    - :meth:`classify` — full semantic drift classification using typed objects.
    """

    def detect(
        self, *, session_fingerprint: str, artifact_fingerprint: str
    ) -> DriftReport:
        """Fingerprint-level drift check (backward-compatible)."""
        if not session_fingerprint or not artifact_fingerprint:
            return DriftReport(
                drift_detected=True,
                drift_type=DRIFT_MISSING,
                remediation_command=_REMEDIATION[DRIFT_MISSING],
                details="One or both fingerprints are empty.",
            )
        if session_fingerprint != artifact_fingerprint:
            return DriftReport(
                drift_detected=True,
                drift_type=DRIFT_MISMATCH,
                remediation_command=_REMEDIATION[DRIFT_MISMATCH],
                details=(
                    f"Session fingerprint '{session_fingerprint}' does not match "
                    f"artifact fingerprint '{artifact_fingerprint}'."
                ),
            )
        return DriftReport(drift_detected=False, drift_type=DRIFT_NONE)

    def classify(
        self,
        *,
        session: SessionState,
        artifact: CompiledArtifact,
        current_profile: str,
    ) -> DriftReport:
        """Full semantic drift classification across all four drift axes.

        Checks are applied in priority order; the first detected drift wins.
        """
        # 1. Profile drift — runtime profile ≠ artifact profile.
        if artifact.profile and current_profile and artifact.profile != current_profile:
            return DriftReport(
                drift_detected=True,
                drift_type=DRIFT_PROFILE,
                remediation_command=_REMEDIATION[DRIFT_PROFILE].replace(
                    "<expected>", artifact.profile
                ),
                details=(
                    f"Current profile '{current_profile}' does not match "
                    f"artifact profile '{artifact.profile}'."
                ),
            )

        # 2. Session drift — session bound to a different artifact fingerprint.
        report = self.detect(
            session_fingerprint=session.artifact_fingerprint,
            artifact_fingerprint=artifact.fingerprint,
        )
        if report.drift_detected:
            if report.drift_type == DRIFT_MISMATCH:
                return DriftReport(
                    drift_detected=True,
                    drift_type=DRIFT_SESSION,
                    remediation_command=_REMEDIATION[DRIFT_SESSION],
                    details=report.details,
                )
            return report  # DRIFT_MISSING — propagate as-is

        # 3. Policy drift — schema version mismatch between session and artifact.
        if session.schema_version != artifact.schema_version:
            return DriftReport(
                drift_detected=True,
                drift_type=DRIFT_POLICY,
                remediation_command=_REMEDIATION[DRIFT_POLICY],
                details=(
                    f"Session schema_version '{session.schema_version}' does not match "
                    f"artifact schema_version '{artifact.schema_version}'."
                ),
            )

        return DriftReport(drift_detected=False, drift_type=DRIFT_NONE)
