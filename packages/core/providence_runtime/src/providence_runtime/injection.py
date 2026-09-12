"""Governance injection — load compiled mandates/policies into runtime scope."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .artifacts import CompiledArtifact


@dataclass
class InjectionResult:
    """Result of a governance injection operation."""

    loaded: bool
    mandates_loaded: int
    policies_loaded: int
    source: str  # "artifact" | "path" | "empty"
    artifact_fingerprint: str = ""
    schema_version: str = ""
    item_ids: list[str] = field(default_factory=list)
    auth_state: str = "unverified"  # "verified" | "degraded" | "unverified"
    trust_source: str = "none"  # "canonical" | "legacy" | "override" | "none"

    @property
    def total_loaded(self) -> int:
        """Total Loaded."""
        return self.mandates_loaded + self.policies_loaded


class GovernanceInjector:
    """Loads governance context from compiled artifacts into runtime session scope.

    The injector is a read-only consumer of compiled artifacts.  It never
    parses canonical source docs — that would violate the Compiler–Runtime
    boundary (§12.2 of the improvement plan).
    """

    def inject_from_artifact(self, artifact: CompiledArtifact) -> InjectionResult:
        """Inject governance from a pre-loaded :class:`CompiledArtifact`."""
        mandates = artifact.items_by_type("MANDATE")
        policies = artifact.items_by_type("POLICY")
        all_items = mandates + policies
        return InjectionResult(
            loaded=True,
            mandates_loaded=len(mandates),
            policies_loaded=len(policies),
            source="artifact",
            artifact_fingerprint=artifact.fingerprint,
            schema_version=artifact.schema_version,
            item_ids=[i.id for i in all_items],
        )

    def inject_from_path(
        self, compiled_dir: Path, profile: str = "master"
    ) -> InjectionResult:
        """Inject governance by loading the artifact at *compiled_dir*."""
        try:
            load_result = CompiledArtifact.from_sdd_compiled_dir_with_auth(
                compiled_dir, profile=profile
            )
        except FileNotFoundError:
            return InjectionResult(
                loaded=False,
                mandates_loaded=0,
                policies_loaded=0,
                source="path",
            )
        result = self.inject_from_artifact(load_result.artifact)
        result.auth_state = load_result.auth_state
        result.trust_source = load_result.trust_source
        return result

    # Backward-compatible shim — kept for tests that use the old signature.
    def inject(self, context_source: str, mandates_loaded: int) -> InjectionResult:
        """Legacy injection stub.  Prefer :meth:`inject_from_artifact`."""
        return InjectionResult(
            loaded=True,
            mandates_loaded=max(0, mandates_loaded),
            policies_loaded=0,
            source=context_source,
        )
