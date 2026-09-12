"""
ArtifactCompiler  Phase 5 step: compile binary artifacts and generate metadata.json.
"""

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from .language_policy import resolve_language_policy


class ArtifactCompiler:
    """Compile mandate/guideline sources to binary and produce metadata.json."""

    def __init__(
        self,
        repo_root: Path,
        sdd_dir: Path,
        runtime_dir: Path,
        mandates: list[dict[str, Any]],
        guidelines: dict[str, dict[str, Any]],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        config: dict[str, Any],
        verbose: bool = False,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.providence_dir = sdd_dir
        self.runtime_dir = runtime_dir
        self.mandates = mandates
        self.guidelines = guidelines
        self.guidelines_by_category = guidelines_by_category
        self.config = config
        self.verbose = verbose
        self._emit = emitter or print

        # Set by generate_metadata(); wrapped by GovernanceInstallSnapshot.from_compiler()
        # and consumed by SeedlingInjector.inject_bootstrap_metadata()
        self.governance_fingerprint: str = "unknown"
        self.generated_at: str = "unknown"

    def _log(self, message: str) -> None:
        if self.verbose:
            self._emit(f"    {message}")

    def compile_artifacts(self) -> bool:
        """Compile mandate.spec and guidelines.dsl to binary format. Non-critical."""
        self._log("Compiling artifacts to binary format")
        try:
            from .mandate_compiler import MandateCompiler

            compiler = MandateCompiler(verbose=self.verbose)

            try:
                import msgpack  # noqa: F401

                fmt = "msgpack"
            except ImportError:
                fmt = "json"

            spec_dir = None
            for candidate in [
                self.repo_root / "spec",
                self.repo_root / "_spec",
                self.repo_root / "docs" / "spec",
            ]:
                if candidate.exists():
                    spec_dir = candidate
                    break

            if not spec_dir:
                self._log(
                    "  No spec source directory found  skipping artifact compilation"
                )
                return True

            mandate_spec = spec_dir / "mandate.spec"
            guidelines_dsl = spec_dir / "guidelines.dsl"

            if mandate_spec.exists():
                success = compiler.compile_mandate_spec(
                    mandate_spec, self.runtime_dir / "mandate.bin", format=fmt
                )
                if not success:
                    self._log("  Failed to compile mandate.spec")
            else:
                self._log(f"  mandate.spec not found at {mandate_spec}")

            if guidelines_dsl.exists():
                success = compiler.compile_guidelines_dsl(
                    guidelines_dsl, self.runtime_dir / "guidelines.bin", format=fmt
                )
                if not success:
                    self._log("  Failed to compile guidelines.dsl")
            else:
                self._log(f"  guidelines.dsl not found at {guidelines_dsl}")

            return True
        except Exception as e:
            self._log(f"  Artifact compilation error: {e}")
            return True  # Non-critical

    def generate_metadata(self) -> bool:
        """Generate metadata.json with compilation info and fingerprints."""
        self._log("Generating metadata.json")
        try:
            import hashlib

            mandate_fingerprints = {}
            for mandate in self.mandates:
                mandate_text = json.dumps(mandate, sort_keys=True)
                fingerprint = hashlib.sha256(mandate_text.encode()).hexdigest()[:16]
                mandate_fingerprints[mandate["id"]] = fingerprint

            all_mandates_text = json.dumps(self.mandates, sort_keys=True)
            combined_fingerprint = hashlib.sha256(
                all_mandates_text.encode()
            ).hexdigest()[:16]

            metadata = {
                "version": "3.0",
                "generated_at": datetime.now().isoformat(),
                "language": self.config.get("language", "Python"),
                "language_context": self.config.get("language_context", {}),
                "language_policy": resolve_language_policy(self.config),
                "adoption_level": self.config.get("adoption_level", "FULL"),
                "mandates_count": len(self.mandates),
                "guidelines_count": len(self.guidelines),
                "categories": list(self.guidelines_by_category.keys()),
                "governance_fingerprint": combined_fingerprint,
                "fingerprints": {
                    "combined": combined_fingerprint,
                    "mandates": mandate_fingerprints,
                },
                "mandates": {m["id"]: m.get("title", "Unknown") for m in self.mandates},
                "structure": {
                    "source": "Governance source of truth for agent queries",
                    "runtime": "Pre-cache instructions for agents",
                    "seedlings": ".vscode, .cursor directories with references to .providence/source",
                },
            }

            metadata_file = self.providence_dir / "metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            self.governance_fingerprint = combined_fingerprint
            self.generated_at = metadata["generated_at"]

            self._log(f"Generated metadata.json (fingerprint: {combined_fingerprint})")
            return True
        except Exception as e:
            self._emit(f"   Failed to generate metadata.json: {e}")
            import traceback

            traceback.print_exc()
            return False
