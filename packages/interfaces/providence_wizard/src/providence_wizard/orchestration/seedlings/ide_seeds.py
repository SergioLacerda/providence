"""Ide Seeds."""

import json
import logging

from providence_wizard.constants import RUNTIME_DIRNAME

from .base_generator import BaseSeedlingGenerator

logger = logging.getLogger(__name__)


class IDESeedsGenerator(BaseSeedlingGenerator):
    """IDESeedsGenerator."""

    def generate_agent_prep_seed(self) -> bool:
        """
        Generate agent-prep.seed.json - IDE integration hooks

        This seedling:
        - Auto-loads governance context in VS Code/Cursor/Windsurf
        - Configures AI agent hooks (Copilot, Claude, etc)
        - Sets up quick access to mandates and guidelines
        - Triggers on project load and editor activation
        """
        try:
            seed_file = self.seedlings_dir / "agent-prep.seed.json"

            adoption_level = self.config.get("adoption_level", "standard")

            seed_data = {
                "auto_activate": True,
                "load_compiled_from": RUNTIME_DIRNAME,
                "on_load": "prepare_agent_context",
                "triggers": ["on_project_load", "on_editor_focus"],
                "description": "AI Agent Preparation - Sets up IDE context for Copilot, Claude, and other agents",
                "required_context": [
                    f"{RUNTIME_DIRNAME}/metadata.json",
                    f"{RUNTIME_DIRNAME}/metadata.json",
                    f"{RUNTIME_DIRNAME}/seedlings/personal-overlay.seed.json",
                ],
                "agent_configuration": {
                    "supported_agents": [
                        "copilot",
                        "claude",
                        "gemini",
                    ],
                    "auto_inject_context": True,
                    "adoption_level": adoption_level,
                    "quick_access": {
                        "compiled": RUNTIME_DIRNAME,
                        "metadata": f"{RUNTIME_DIRNAME}/metadata.json",
                    },
                },
                "ide_hooks": {
                    "vscode": {
                        "instructions_ref": ".vscode/ai-rules.md",
                        "auto_load": True,
                    },
                    "cursor": {
                        "rules_ref": ".cursor/rules/sdd-governance.mdc",
                        "auto_load": True,
                    },
                    "claude": {
                        "instructions_ref": "CLAUDE.md",
                        "auto_load": True,
                    },
                    "gemini": {
                        "instructions_ref": "GEMINI.md",
                        "auto_load": True,
                    },
                },
                "governance_fingerprint": self.spec_fingerprint,
                "mandates_count": len(self.mandate_ids),
                "generated_at": self.generated_at,
            }

            with open(seed_file, "w", encoding="utf-8") as f:
                json.dump(seed_data, f, indent=2)

            self.log(" Generated agent-prep.seed.json")
            return True
        except Exception as e:
            logger.warning(f"   Failed to generate agent-prep.seed.json: {e}")
            return False

    def generate_personal_overlay_seed(self) -> bool:
        """Generate personal-overlay.seed.json for dynamic personal+SDD capability merge."""
        try:
            seed_file = self.seedlings_dir / "personal-overlay.seed.json"
            seed_data = {
                "schema_version": "1.0.0",
                "auto_activate": True,
                "load_compiled_from": RUNTIME_DIRNAME,
                "on_load": "prepare_personal_overlay",
                "triggers": ["on_project_load", "on_editor_focus"],
                "description": f"Personal seed overlay - merges personal .agents skills with governed {RUNTIME_DIRNAME} registries",
                "required_context": [
                    f"{RUNTIME_DIRNAME}/skills/registry.json",
                    f"{RUNTIME_DIRNAME}/commands/registry.json",
                ],
                "governance_fingerprint": self.spec_fingerprint,
                "mandates_count": len(self.mandate_ids),
                "generated_at": self.generated_at,
            }
            with open(seed_file, "w", encoding="utf-8") as f:
                json.dump(seed_data, f, indent=2)
            self.log(" Generated personal-overlay.seed.json")
            return True
        except Exception as e:
            logger.warning(f"   Failed to generate personal-overlay.seed.json: {e}")
            return False

    def generate_vscode_seed(self) -> bool:
        """Generate vscode.seed.json  lightweight redirector for VS Code."""
        try:
            seed_file = self.seedlings_dir / "vscode.seed.json"
            seed_data = {
                "auto_activate": True,
                "agent": "vscode",
                "description": "VS Code governance bootstrap  redirects to compiled SDD source",
                "load_compiled_from": RUNTIME_DIRNAME,
                "instructions_ref": ".vscode/ai-rules.md",
                "settings_ref": ".vscode/settings.json",
                "governance_fingerprint": self.spec_fingerprint,
                "mandates_count": len(self.mandate_ids),
                "auto_load": True,
                "triggers": ["on_project_load", "on_editor_focus"],
                "required_context": [
                    f"{RUNTIME_DIRNAME}/metadata.json",
                    ".vscode/ai-rules.md",
                ],
                "on_load": "prepare_ide_context",
                "generated_at": self.generated_at,
            }
            with open(seed_file, "w", encoding="utf-8") as f:
                json.dump(seed_data, f, indent=2)
            self.log(" Generated vscode.seed.json")
            return True
        except Exception as e:
            logger.warning(f"   Failed to generate vscode.seed.json: {e}")
            return False

    def generate_cursor_seed(self) -> bool:
        """Generate cursor.seed.json  lightweight redirector for Cursor IDE."""
        try:
            seed_file = self.seedlings_dir / "cursor.seed.json"
            seed_data = {
                "auto_activate": True,
                "agent": "cursor",
                "description": "Cursor IDE governance bootstrap  redirects to compiled SDD source",
                "load_compiled_from": RUNTIME_DIRNAME,
                "instructions_ref": ".cursor/rules/sdd-governance.mdc",
                "commands_ref": ".cursor/rules/sdd-commands.mdc",
                "governance_fingerprint": self.spec_fingerprint,
                "mandates_count": len(self.mandate_ids),
                "auto_load": True,
                "triggers": ["on_project_load", "on_editor_focus"],
                "required_context": [
                    f"{RUNTIME_DIRNAME}/metadata.json",
                    ".cursor/rules/sdd-governance.mdc",
                ],
                "on_load": "prepare_ide_context",
                "generated_at": self.generated_at,
            }
            with open(seed_file, "w", encoding="utf-8") as f:
                json.dump(seed_data, f, indent=2)
            self.log(" Generated cursor.seed.json")
            return True
        except Exception as e:
            logger.warning(f"   Failed to generate cursor.seed.json: {e}")
            return False
