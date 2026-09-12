"""Typed representation of a compiled governance artifact."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from providence_core.utils.environment import find_workspace_root

from ._governance_item import GovernanceItem
from ._item_type import _resolve_item_type

logger = logging.getLogger(__name__)


@dataclass
class CompiledArtifact:
    """Typed representation of a compiled governance artifact.

    Mandatory fields per the Compiler–Runtime Boundary Contract (§12.3):
      artifact_version, schema_version, fingerprint, generated_at.
    """

    artifact_version: str
    schema_version: str
    fingerprint: str
    generated_at: str
    profile: str  # master | client
    items: list[GovernanceItem] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Derived helpers                                                       #
    # ------------------------------------------------------------------ #

    def items_by_type(self, item_type: str) -> list[GovernanceItem]:
        """Return items matching *item_type* (case-insensitive)."""
        upper = item_type.upper()
        return [i for i in self.items if i.item_type.upper() == upper]

    def find_by_id(self, item_id: str) -> GovernanceItem | None:
        """Return first item whose id matches (case-insensitive)."""
        lower = item_id.lower()
        return next((i for i in self.items if i.id.lower() == lower), None)

    # ------------------------------------------------------------------ #
    # Factory methods                                                       #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_governance_json(
        cls,
        items_path: Path,
        metadata_path: Path | None = None,
        profile: str = "master",
    ) -> CompiledArtifact:
        """Load from the JSON pair produced by the compiler.

        *items_path*    — governance-core.json (contains items + fingerprint).
        *metadata_path* — metadata-core.json (contains generated_at, version).
        """
        data = json.loads(items_path.read_text(encoding="utf-8"))
        fingerprint: str = data.get("fingerprint", "")
        version: str = str(data.get("version", "0.0"))
        generated_at: str = ""

        if metadata_path and metadata_path.exists():
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            generated_at = str(meta.get("generated_at", ""))
            version = str(meta.get("version", version))

        items: list[GovernanceItem] = []
        for raw in data.get("items", []):
            meta_block: dict[str, object] = raw.get("metadata", {})
            raw_type, type_source = _resolve_item_type(raw, meta_block)
            if type_source == "metadata.type":
                logger.debug(
                    "legacy item type fallback used for id=%s (metadata.type)",
                    raw.get("id", ""),
                )
            elif type_source == "missing":
                logger.debug(
                    "item type missing for id=%s; defaulting to UNKNOWN",
                    raw.get("id", ""),
                )

            # G6: Mapeamento de campos de sumário com fallbacks
            items.append(
                GovernanceItem(
                    id=str(raw.get("id", "")),
                    title=str(raw.get("title", "")),
                    item_type=raw_type,
                    description=str(
                        meta_block.get(
                            "description", raw.get("summary_description", "")
                        )
                    ),
                    rationale=str(
                        meta_block.get("rationale", raw.get("summary_rationale", ""))
                    ),
                    summary_minimal=str(
                        meta_block.get(
                            "summary_minimal", raw.get("summary_minimal", "")
                        )
                    ),
                    summary_runtime=str(
                        meta_block.get(
                            "summary_runtime", raw.get("summary_runtime", "")
                        )
                    ),
                    summary_full=str(
                        meta_block.get("summary_full", raw.get("summary_full", ""))
                    ),
                    criticality=str(
                        meta_block.get("criticality", raw.get("criticality", ""))
                    ),
                )
            )

        return cls(
            artifact_version=version,
            schema_version=version,
            fingerprint=fingerprint,
            generated_at=generated_at,
            profile=profile,
            items=items,
        )

    @classmethod
    def from_sdd_compiled_dir(
        cls, compiled_dir: Path, profile: str = "master"
    ) -> CompiledArtifact:
        """Convenience: load core artifact from a compiled/ directory.

        Returns a bare CompiledArtifact. For authentication metadata (auth_state, trust_source),
        use from_sdd_compiled_dir_with_auth() instead.
        """
        items_path = compiled_dir / "governance-core.json"
        metadata_path = compiled_dir / "audit" / "metadata-core.json"
        if not metadata_path.exists():
            metadata_path = compiled_dir / "metadata-core.json"
        if not items_path.exists():
            raise FileNotFoundError(f"governance-core.json not found in {compiled_dir}")
        artifact = cls.from_governance_json(items_path, metadata_path, profile=profile)
        return artifact

    @classmethod
    def from_sdd_compiled_dir_with_auth(
        cls, compiled_dir: Path, profile: str = "master"
    ) -> ArtifactLoadResult:
        """Load core artifact with authentication metadata (auth_state, trust_source).

        Validates artifact signature if SDD_SIGNATURE_MODE is set (warn/strict).
        Returns an ArtifactLoadResult with auth_state indicating signature verification result.
        """
        auth_state = "unverified"
        trust_source = "canonical"

        signature_mode = os.environ.get("SDD_SIGNATURE_MODE", "warn").strip().lower()
        if signature_mode in {"warn", "strict"}:
            from ..signatures import validate_artifact_signature

            # Find workspace root to anchor keyring path
            workspace_root = find_workspace_root(compiled_dir)
            core_artifact = compiled_dir / "governance-core.json"
            if core_artifact.exists():
                result = validate_artifact_signature(
                    artifact_path=core_artifact,
                    sig_path=core_artifact.with_suffix(core_artifact.suffix + ".sig"),
                    strict=signature_mode == "strict",
                    workspace_root=workspace_root,
                )
                if result.blocking and not result.ok:
                    raise RuntimeError(f"{result.code}: {result.reason}")
                # Set auth_state based on signature validation result
                if result.ok:
                    auth_state = "verified"
                elif signature_mode == "warn":
                    # Non-blocking failure in warn mode → degraded auth
                    auth_state = "degraded"
                # Capture actual trust_source from signature validation result
                trust_source = result.trust_source

        items_path = compiled_dir / "governance-core.json"
        metadata_path = compiled_dir / "audit" / "metadata-core.json"
        if not metadata_path.exists():
            metadata_path = compiled_dir / "metadata-core.json"
        if not items_path.exists():
            raise FileNotFoundError(f"governance-core.json not found in {compiled_dir}")
        artifact = cls.from_governance_json(items_path, metadata_path, profile=profile)

        return ArtifactLoadResult(
            artifact=artifact,
            auth_state=auth_state,
            trust_source=trust_source,
        )

    @classmethod
    async def from_sdd_compiled_dir_async(
        cls, compiled_dir: Path, profile: str = "master"
    ) -> CompiledArtifact:
        """Async wrapper for loading the local core artifact."""
        return cls.from_sdd_compiled_dir(compiled_dir, profile)

    @classmethod
    async def from_sdd_compiled_dir_with_auth_async(
        cls, compiled_dir: Path, profile: str = "master"
    ) -> ArtifactLoadResult:
        """Async wrapper for loading the local core artifact with auth metadata."""
        return cls.from_sdd_compiled_dir_with_auth(compiled_dir, profile)


@dataclass
class ArtifactLoadResult:
    """Result of loading a compiled artifact with authentication metadata."""

    artifact: CompiledArtifact
    auth_state: str = "unverified"  # "verified" | "degraded" | "unverified"
    trust_source: str = "none"  # "canonical" | "legacy" | "override" | "none"
