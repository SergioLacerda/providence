"""GovernanceInstallSnapshot  single aggregation of governance data compiled in Phase 5.

Wraps the mandates/guidelines/fingerprint/timestamp already produced by
ArtifactCompiler so downstream consumers (bootstrap metadata injection, IDE
rule population, agent-instructions rendering) read from one object instead of
independently recomputing or re-reading the compiler's attributes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .phase5_artifact_compiler import ArtifactCompiler


@dataclass(frozen=True)
class GovernanceInstallSnapshot:
    """Aggregated governance state produced by a single Phase 5 compilation run."""

    mandates: list[dict[str, Any]] = field(default_factory=list)
    guidelines: dict[str, dict[str, Any]] = field(default_factory=dict)
    guidelines_by_category: dict[str, list[dict[str, Any]]] = field(
        default_factory=dict
    )
    governance_fingerprint: str = "unknown"
    generated_at: str = "unknown"
    schema_version: str = "1"
    workspace_root: str = "unknown"
    fingerprint_source: str = "unknown"
    mandates_count: int = 0
    mandate_ids: list[str] = field(default_factory=list)
    language_context: dict[str, Any] = field(default_factory=dict)
    handshake_mode: str = "standard"
    selected_agents: list[str] = field(default_factory=list)
    hook_agents: list[str] = field(default_factory=list)
    generated_surfaces: list[str] = field(default_factory=list)

    @classmethod
    def from_compiler(
        cls,
        compiler: ArtifactCompiler,
        *,
        workspace_root: str = "unknown",
        handshake_mode: str = "standard",
        selected_agents: list[str] | None = None,
        hook_agents: list[str] | None = None,
        generated_surfaces: list[str] | None = None,
    ) -> GovernanceInstallSnapshot:
        """Build a snapshot from an ArtifactCompiler after generate_metadata() has run.

        `workspace_root`, `handshake_mode`, `selected_agents`, `hook_agents`, and
        `generated_surfaces` are not derivable from the compiler alone (they come from
        the wizard's resolved preferences/config)  callers pass them explicitly when
        available; each has a safe default so existing call sites keep working unchanged.
        """
        mandate_ids = [
            str(m["id"]) for m in compiler.mandates if isinstance(m, dict) and "id" in m
        ]
        return cls(
            mandates=compiler.mandates,
            guidelines=compiler.guidelines,
            guidelines_by_category=compiler.guidelines_by_category,
            governance_fingerprint=compiler.governance_fingerprint,
            generated_at=compiler.generated_at,
            workspace_root=workspace_root,
            fingerprint_source="compiler.governance_fingerprint",
            mandates_count=len(compiler.mandates),
            mandate_ids=mandate_ids,
            handshake_mode=handshake_mode,
            selected_agents=selected_agents or [],
            hook_agents=hook_agents or [],
            generated_surfaces=generated_surfaces or [],
        )
