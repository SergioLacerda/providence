"""Artifact Bootstrapper - On-demand compilation for clean environments.

Generates Phase 1+2 governance artifacts when they're missing (CI, Docker).
"""

import shutil
from collections.abc import Callable
from pathlib import Path

# Canonical artifact filenames (must stay in sync across all phases)
GOVERNANCE_ARTIFACTS = (
    "governance-core.compiled.msgpack",
    "governance-client-template.compiled.msgpack",
    "metadata-core.json",
    "metadata-client-template.json",
)


class ArtifactBootstrapper:
    """On-demand artifact generation for clean environments (CI, Docker)."""

    def __init__(
        self,
        compiled_dir: Path,
        master_compiled_dir: Path,
        repo_root: Path,
        metadata_source_fn: Callable[[str], Path],
        emit_fn: Callable[[str], None] | None = None,
    ):
        """Initialize bootstrapper."""
        self.compiled_dir = compiled_dir
        self.master_compiled_dir = master_compiled_dir
        self.repo_root = repo_root
        self._metadata_source = metadata_source_fn
        self._emit = emit_fn

    def _out(self, message: str) -> None:
        """Emit status message."""
        if self._emit is not None:
            self._emit(message)

    def _ensure_audit_metadata(self) -> None:
        """Ensure metadata files exist in audit/ subdirectory (copy from root if needed)."""
        audit_dir = self.compiled_dir / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        for filename in GOVERNANCE_ARTIFACTS[2:]:
            dst = audit_dir / filename
            if dst.exists():
                continue
            src = self.compiled_dir / filename
            if src.exists():
                shutil.copy2(src, dst)

    def ensure(self) -> None:
        """Generate compiled artifacts on-demand for clean environments."""
        required_files = [
            self.compiled_dir / GOVERNANCE_ARTIFACTS[0],
            self.compiled_dir / GOVERNANCE_ARTIFACTS[1],
            self._metadata_source(GOVERNANCE_ARTIFACTS[2]),
            self._metadata_source(GOVERNANCE_ARTIFACTS[3]),
        ]

        if all(file.exists() for file in required_files):
            # Artifacts are present but audit/ may be missing metadata
            # (e.g. compile wrote to root only). Propagate before returning.
            self._ensure_audit_metadata()
            return

        try:
            from providence_core.governance_orchestrator import GovernanceOrchestrator

            self._out("  ℹ️  Missing compiled artifacts, running PHASE 1+2 bootstrap...")
            orchestrator = GovernanceOrchestrator(str(self.repo_root))
            result = orchestrator.run_full_pipeline()
            if not result or not result.get("full_pipeline_success"):
                self._out("  ❌ Bootstrap pipeline failed")
                return
            self._sync_client_compiled_from_master()
        except Exception as e:
            self._out(f"  ❌ Failed to bootstrap compiled artifacts: {e}")

    def _sync_client_compiled_from_master(self) -> None:
        """Ensure client_compiled receives compiled artifacts from master build output."""
        self.compiled_dir.mkdir(parents=True, exist_ok=True)
        audit_dir = self.compiled_dir / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        master_audit = self.master_compiled_dir / "audit"

        for filename in GOVERNANCE_ARTIFACTS[:2]:  # msgpack files
            src = self.master_compiled_dir / filename
            dst = self.compiled_dir / filename
            if src.exists():
                shutil.copy2(src, dst)

        for filename in GOVERNANCE_ARTIFACTS[2:]:  # metadata files
            src = master_audit / filename
            if not src.exists():
                src = self.master_compiled_dir / filename
            dst = audit_dir / filename
            if src.exists():
                shutil.copy2(src, dst)
