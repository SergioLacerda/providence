"""Security audit logic for SDD Governance (007 inspired)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from providence_runtime.signatures import (
    _resolve_keyring_path,
    validate_compiled_signatures,
)

from providence_core.utils.environment import find_workspace_root

logger = logging.getLogger(__name__)


@dataclass
class AuditIssue:
    """AuditIssue."""

    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str
    message: str
    remediation: str


@dataclass
class AuditReport:
    """AuditReport."""

    ok: bool
    score: int
    issues: list[AuditIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class GovernanceAuditor:
    """GovernanceAuditor."""

    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = workspace_root or find_workspace_root()

    def perform_audit(self) -> AuditReport:
        """Perform Audit."""
        issues: list[AuditIssue] = []
        metadata: dict[str, Any] = {}

        ws = self.workspace_root
        if ws is None:
            return AuditReport(
                ok=False,
                score=0,
                issues=[
                    AuditIssue(
                        "HIGH",
                        "Workspace",
                        "No SDD workspace found",
                        "Run 'providence init'",
                    )
                ],
            )

        # 1. Keyring & Signature Audit
        self._audit_signatures(ws, issues, metadata)

        # 2. Path & Permissions Audit
        self._audit_paths(ws, issues, metadata)

        # 3. Environment Audit
        self._audit_env(issues, metadata)

        # Calculate score (starting at 100)
        score = 100
        for issue in issues:
            if issue.severity == "CRITICAL":
                score -= 40
            elif issue.severity == "HIGH":
                score -= 20
            elif issue.severity == "MEDIUM":
                score -= 10
            elif issue.severity == "LOW":
                score -= 5

        score = max(0, score)
        return AuditReport(
            ok=score >= 70, score=score, issues=issues, metadata=metadata
        )

    def _audit_signatures(
        self, ws: Path, issues: list[AuditIssue], metadata: dict[str, Any]
    ) -> None:
        compiled_dir = ws / ".providence" / "compiled"
        if not compiled_dir.is_dir():
            issues.append(
                AuditIssue(
                    "HIGH",
                    "Integrity",
                    "No compiled governance artifacts found",
                    "Run 'providence governance compile'",
                )
            )
            return

        # Check keyring resolution
        keyring_path, source, warning = _resolve_keyring_path(
            compiled_dir, strict=False
        )
        metadata["keyring_source"] = source
        if source == "legacy":
            issues.append(
                AuditIssue(
                    "MEDIUM",
                    "Trust",
                    "Using legacy keyring location",
                    "Move trusted-keys.json to .providence/trust/",
                )
            )
        elif source == "none":
            issues.append(
                AuditIssue(
                    "CRITICAL",
                    "Trust",
                    "No trusted keyring found",
                    "Initialize keyring in .providence/trust/",
                )
            )

        # Check signatures
        sig_results = validate_compiled_signatures(compiled_dir, strict=False)
        invalid_count = sum(1 for r in sig_results if not r.ok)
        if invalid_count > 0:
            issues.append(
                AuditIssue(
                    "CRITICAL",
                    "Integrity",
                    f"{invalid_count} artifacts have invalid/missing signatures",
                    "Re-sign artifacts with 'providence governance sign'",
                )
            )

        metadata["verified_artifacts"] = len([r for r in sig_results if r.ok])

    def _audit_paths(
        self, ws: Path, issues: list[AuditIssue], metadata: dict[str, Any]
    ) -> None:
        # Check permissions of sensitive dirs
        trust_dir = ws / ".providence" / "trust"
        if trust_dir.is_dir():
            mode = trust_dir.stat().st_mode & 0o777
            if mode > 0o755:
                issues.append(
                    AuditIssue(
                        "MEDIUM",
                        "Permissions",
                        f"Trust directory has insecure permissions: {oct(mode)}",
                        "chmod 700 .providence/trust/",
                    )
                )

    def _audit_env(self, issues: list[AuditIssue], metadata: dict[str, Any]) -> None:
        import os

        mode = os.environ.get("SDD_SIGNATURE_MODE", "warn").lower()
        metadata["signature_mode"] = mode
        if mode == "off":
            issues.append(
                AuditIssue(
                    "HIGH",
                    "Configuration",
                    "Signature validation is explicitly disabled (SDD_SIGNATURE_MODE=off)",
                    "Set SDD_SIGNATURE_MODE=warn or strict",
                )
            )
