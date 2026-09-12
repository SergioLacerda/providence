"""Intelligent Seedlings Generator."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providence_core.utils.text_io import read_text_utf8
from providence_wizard.constants import RUNTIME_DIRNAME

from ._seedlings_helpers import _validate_awareness_pack, _write_deployment_manifest
from .seedlings.ai_seeds import AISeedsGenerator
from .seedlings.governance_seeds import GovernanceSeedsGenerator
from .seedlings.ide_seeds import IDESeedsGenerator
from .seedlings.sovereign_factory import SovereignFactoryGenerator


class IntelligentSeedlingsGenerator:
    """Generate intelligent, customized seedling files for AI agents"""

    def __init__(
        self,
        output_base: Path,
        mandates: list[dict[str, Any]],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        config: dict[str, Any],
        governance_core_path: Path,
        verbose: bool = False,
    ):
        self.output_base = output_base
        self.seedlings_dir = output_base / RUNTIME_DIRNAME / "seedlings"
        self.mandates = mandates
        self.guidelines_by_category = guidelines_by_category
        self.config = config
        self.governance_core_path = governance_core_path
        self.verbose = verbose

        self.spec_fingerprint = self._compute_fingerprint()
        self.mandate_ids = self._extract_mandate_ids()
        self.active_categories = list(guidelines_by_category.keys())
        self.generated_at = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        self.ai_gen = AISeedsGenerator(
            output_base,
            self.seedlings_dir,
            config,
            self.spec_fingerprint,
            self.mandate_ids,
            self.active_categories,
            self.generated_at,
            verbose,
        )
        self.ide_gen = IDESeedsGenerator(
            output_base,
            self.seedlings_dir,
            config,
            self.spec_fingerprint,
            self.mandate_ids,
            self.active_categories,
            self.generated_at,
            verbose,
        )
        self.gov_gen = GovernanceSeedsGenerator(
            output_base,
            self.seedlings_dir,
            config,
            self.spec_fingerprint,
            self.mandate_ids,
            self.active_categories,
            self.generated_at,
            verbose,
        )
        self.sovereign_gen = SovereignFactoryGenerator(
            output_base,
            self.seedlings_dir,
            config,
            self.spec_fingerprint,
            self.mandate_ids,
            self.active_categories,
            self.generated_at,
            verbose,
        )

        # Inject the mandate objects into the gov gen specifically since it needs it
        self.gov_gen.mandates = self.mandates
        self._awareness_pack: dict[str, Any] = {
            "status": "unknown",
            "mode": "unknown",
            "missing_items": [],
        }

    def log(self, message: str) -> None:
        """Log."""
        if self.verbose:
            print(f"    {message}")  # noqa: T201

    def _compute_fingerprint(self) -> str:
        try:
            if self.governance_core_path.exists():
                content = read_text_utf8(self.governance_core_path)
                clean_content = json.dumps(json.loads(content), separators=(",", ":"))
                return hashlib.sha256(clean_content.encode()).hexdigest()[:8]
        except Exception:  # nosec B110 noqa: BLE001  intentional fallback; corrupted/missing file is non-fatal
            pass
        return "00000000"

    def get_summary(self) -> dict[str, Any]:
        """Get Summary."""
        summary = self.gov_gen.get_summary()
        summary["awareness_pack"] = self._awareness_pack
        return summary

    def _validate_awareness_pack(self) -> dict[str, Any]:
        return _validate_awareness_pack(
            self.output_base, self.seedlings_dir, self.gov_gen.prompt_commands_mode
        )

    def _extract_mandate_ids(self) -> list[str]:
        return sorted([m["id"] for m in self.mandates if m.get("id")])

    def generate_all(self, selected: set[str] | None = None) -> bool:
        """Generate All."""
        self.log("Generating intelligent seedlings")
        try:
            self.seedlings_dir.mkdir(parents=True, exist_ok=True)
            self.log(f"Created seedlings directory: {self.seedlings_dir}")

            generators = {
                "governance": self.gov_gen.generate_governance_seed,
                "agent-prep": self.ide_gen.generate_agent_prep_seed,
                "personal-overlay": self.ide_gen.generate_personal_overlay_seed,
                "compliance": self.gov_gen.generate_compliance_seed,
                "activation-guide": self.gov_gen.generate_activation_guide,
                "verify": self.gov_gen.generate_verification_script,
                "agnostic-instructions": self.gov_gen.generate_agnostic_agent_instructions,
                "gemini": self.ai_gen.generate_gemini_seed,
                "antigravity": self.ai_gen.generate_antigravity_seed,
                "copilot": self.ai_gen.generate_copilot_seed,
                "vscode": self.ide_gen.generate_vscode_seed,
                "cursor": self.ide_gen.generate_cursor_seed,
                "claude": self.ai_gen.generate_claude_seed,
                "codex": self.ai_gen.generate_codex_seed,
                "prompt-commands": self.gov_gen.generate_prompt_commands,
                "agents-md": self.gov_gen.generate_agents_md,
                "sovereign-factory": self.sovereign_gen.generate_sovereign_factory_seed,
            }

            # `None` preserves the historical full-generation contract used by
            # direct orchestrator/e2e paths. The interactive wizard should pass
            # an explicit selection when it wants the recommended subset.
            resolved = set(generators) if selected is None else set(selected)
            # `agnostic-instructions` and `sovereign-factory` are internal,
            # always-on helper artifacts not exposed in the selection catalog.
            resolved |= {"agnostic-instructions", "sovereign-factory"}
            to_run = {k: v for k, v in generators.items() if k in resolved}
            results = [fn() for fn in to_run.values()]
            success = all(results)
            self._awareness_pack = self._validate_awareness_pack()
            # Full generation must fail closed when awareness contract is incomplete.
            if selected is None and self._awareness_pack["status"] != "ok":
                success = False

            if success:
                self.log(f" Generated {len(to_run)} seedling/prompt artifacts")
                self._write_deployment_manifest()
            else:
                print("   Some seedling files failed to generate")  # noqa: T201
            return success
        except Exception as e:
            print(f"   Failed to generate seedlings: {e}")  # noqa: T201
            return False

    def _write_deployment_manifest(self) -> None:
        """Write DEPLOYMENT_MANIFEST.json with fingerprints of all bootstrap files."""
        _write_deployment_manifest(
            self.output_base, self.spec_fingerprint, self.generated_at, self.log
        )
