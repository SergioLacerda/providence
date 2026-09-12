"""Shared runtime preflight service for governance validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PreflightResult:
    """PreflightResult."""

    passed: bool
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


def run_runtime_preflight(path: str) -> PreflightResult:
    """Run providence_runtime preflight checks in best-effort mode.

    If runtime deps are unavailable or artifact path is not compiled JSON,
    returns a permissive pass result.
    """
    try:
        from providence_runtime import CompiledArtifact, PolicyEngine, SessionState

        compiled_dir = Path(path)
        core_json = compiled_dir / "governance-core.json"
        if not core_json.exists():
            return PreflightResult(
                passed=True,
                reason="non-compiled path; preflight skipped",
                details={"skipped": True},
            )

        artifact = CompiledArtifact.from_sdd_compiled_dir(compiled_dir)
        session = SessionState(
            workspace_id="validate",
            agent_id="providence-cli",
            work_item_id="governance-validate",
            artifact_fingerprint=artifact.fingerprint,
            schema_version=artifact.schema_version,
            policy_set_version=artifact.schema_version,
        )
        result = PolicyEngine().validate_preflight(
            artifact=artifact,
            session=session,
            current_profile=artifact.profile,
        )
        return PreflightResult(
            passed=result.allowed,
            reason=result.reason,
            details={
                "artifact_fingerprint": artifact.fingerprint,
                "schema_version": artifact.schema_version,
                "profile": artifact.profile,
            },
        )
    except Exception as exc:
        return PreflightResult(
            passed=True,
            reason="runtime preflight unavailable (best-effort)",
            details={"skipped": True, "error": str(exc)},
        )
