"""
SeedlingsOrchestrator  Phase 6 step: generate .providence/seedlings/ files.

Supports selective generation: pass a set of seedling keys to generate only
the chosen ones. Omit (or pass None) to generate all (default behaviour).

Available seedling keys:
    "governance", "agent-prep", "personal-overlay", "compliance",
    "activation-guide", "verify",
    "copilot", "gemini", "codex", "vscode", "cursor", "claude",
    "prompt-commands"
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from providence_core.utils.log import get_logger

from .intelligent_seedlings_generator import IntelligentSeedlingsGenerator

logger = get_logger(__name__)


class SeedlingsOrchestrator:
    """Delegate to IntelligentSeedlingsGenerator with optional seedling filtering."""

    def __init__(
        self,
        output_base: Path,
        mandates: list[dict[str, Any]],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        config: dict[str, Any],
        governance_core_path: Path,
        paths: dict[str, Any],
        verbose: bool = False,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self.output_base = output_base
        self.mandates = mandates
        self.guidelines_by_category = guidelines_by_category
        self.config = config
        self.governance_core_path = governance_core_path
        self.paths = paths
        self.verbose = verbose
        self._emit = emitter or print

    def _log(self, message: str) -> None:
        if self.verbose:
            self._emit(message)
        else:
            logger.debug(message)

    def _resolve_governance_path(self) -> Path:
        client_compiled = Path(self.paths.get("client_compiled", ""))
        master_compiled = Path(self.paths.get("master_compiled", ""))
        candidates: list[Path] = [
            self.governance_core_path,
            client_compiled / "source" / "governance-core.json",
            master_compiled / "source" / "governance-core.json",
        ]
        for path in candidates:
            if path and path.exists():
                return path
        self._log(f"  governance-core.json not found in {candidates}")
        return self.governance_core_path  # best-effort fallback

    def generate(self, selected: set[str] | None = None) -> bool:
        """Generate seedlings.

        Args:
            selected: Set of seedling keys to generate. None generates all.

        Returns:
            True if all requested seedlings were generated successfully.
        """
        self._log("Generating intelligent seedlings")
        try:
            governance_path = self._resolve_governance_path()
            generator = IntelligentSeedlingsGenerator(
                output_base=self.output_base,
                mandates=self.mandates,
                guidelines_by_category=self.guidelines_by_category,
                config=self.config,
                governance_core_path=governance_path,
                verbose=self.verbose,
            )

            if not generator.generate_all(selected=selected):
                self._emit("   Failed to generate intelligent seedlings")
                return False

            summary = generator.get_summary()
            self._log(f" Generated {summary['count']} intelligent seedlings")
            self._log(f"   Fingerprint: {summary['fingerprint']}")
            self._log(f"   Mandates: {', '.join(summary['mandates'])}")
            self._log(f"   Categories: {', '.join(summary['guidelines'])}")
            return True
        except Exception as e:
            self._emit(f"   Failed to generate intelligent seedlings: {e}")
            import traceback

            traceback.print_exc()
            return False
