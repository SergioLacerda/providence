"""Ai Seeds."""

import json
import logging
from pathlib import Path

from providence_core.utils.managed_block import merge_managed_block
from providence_core.utils.text_io import read_text_utf8, write_text_utf8
from providence_wizard.constants import RUNTIME_DIRNAME

from ._ai_seed_templates import (
    CLAUDE_BOOTSTRAP_SCRIPT,
    CLAUDE_SETTINGS,
    build_claude_md,
    build_copilot_instructions,
)
from ._renderer import build_fingerprint_header, render_agent_redirector
from .base_generator import BaseSeedlingGenerator

logger = logging.getLogger(__name__)


def _write_root_seed_file(path: Path, block_body: str) -> None:
    """Write *block_body* into *path*'s sdd-managed block, preserving the rest.

    `path` is a root-level, cross-tool-convention filename (`CLAUDE.md`,
    `GEMINI.md`, `AGENTS.md`) that other tools/agents/humans may also write
    to  see
    `.analysis/refined/20260906-root-seed-githook-necessity/design.md`.
    Raises `MalformedManagedBlockError` if the existing file has unbalanced
    markers; callers must let this propagate (report failure), never catch
    it to fall back to a whole-file overwrite.
    """
    existing = read_text_utf8(path) if path.exists() else None
    merged = merge_managed_block(existing, block_body)
    write_text_utf8(path, merged)


class AISeedsGenerator(BaseSeedlingGenerator):
    """AISeedsGenerator."""

    def generate_gemini_seed(self) -> bool:
        """Generate Gemini CLI governance bootstrap: GEMINI.md, settings.json, seed.json."""
        try:
            gemini_dir = self.output_base / ".gemini"
            gemini_dir.mkdir(parents=True, exist_ok=True)
            redirector_content = render_agent_redirector(
                tool_name="Gemini",
                config_paths=[
                    ".gemini/commands.md",
                    ".gemini/antigravity/skills/",
                    "GEMINI.md",
                ],
                fingerprint=self.spec_fingerprint,
                mandate_ids=self.mandate_ids,
                generated_at=self.generated_at,
            )
            write_text_utf8(gemini_dir / "gemini-instructions.md", redirector_content)
            _write_root_seed_file(self.output_base / "GEMINI.md", redirector_content)
            settings = {"contextFileName": "GEMINI.md"}
            write_text_utf8(
                gemini_dir / "settings.json", json.dumps(settings, indent=2) + "\n"
            )
            seed_data = {
                "auto_activate": True,
                "agent": "gemini",
                "description": "Gemini CLI governance bootstrap  redirects to compiled SDD source",
                "load_compiled_from": RUNTIME_DIRNAME,
                "instructions_ref": "GEMINI.md",
                "commands_ref": ".gemini/commands.md",
                "governance_fingerprint": self.spec_fingerprint,
                "mandates_count": len(self.mandate_ids),
                "auto_load": True,
                "triggers": ["on_project_load", "on_editor_focus"],
                "required_context": [f"{RUNTIME_DIRNAME}/metadata.json", "GEMINI.md"],
                "on_load": "prepare_ide_context",
                "generated_at": self.generated_at,
            }
            write_text_utf8(
                self.seedlings_dir / "gemini.seed.json",
                json.dumps(seed_data, indent=2) + "\n",
            )
            self.log(
                " Generated Gemini seed (GEMINI.md, settings.json, gemini.seed.json)"
            )
            return True
        except Exception as e:
            logger.warning(f"   Failed to generate Gemini seed: {e}")
            return False

    def generate_antigravity_seed(self) -> bool:
        """Generate Antigravity IDE governance bootstrap, separate from Gemini CLI."""
        try:
            antigravity_dir = self.output_base / ".gemini" / "antigravity"
            antigravity_dir.mkdir(parents=True, exist_ok=True)
            redirector_content = render_agent_redirector(
                tool_name="Antigravity",
                config_paths=[
                    ".gemini/antigravity/skills/",
                    ".gemini/antigravity/antigravity-instructions.md",
                ],
                fingerprint=self.spec_fingerprint,
                mandate_ids=self.mandate_ids,
                generated_at=self.generated_at,
            )
            _write_root_seed_file(
                antigravity_dir / "antigravity-instructions.md", redirector_content
            )
            seed_data = {
                "auto_activate": True,
                "agent": "antigravity",
                "description": "Antigravity IDE governance bootstrap  redirects to compiled SDD source",
                "load_compiled_from": RUNTIME_DIRNAME,
                "instructions_ref": ".gemini/antigravity/antigravity-instructions.md",
                "governance_fingerprint": self.spec_fingerprint,
                "mandates_count": len(self.mandate_ids),
                "auto_load": True,
                "triggers": ["on_project_load", "on_editor_focus"],
                "required_context": [
                    f"{RUNTIME_DIRNAME}/metadata.json",
                    ".gemini/antigravity/antigravity-instructions.md",
                ],
                "on_load": "prepare_ide_context",
                "generated_at": self.generated_at,
            }
            write_text_utf8(
                self.seedlings_dir / "antigravity.seed.json",
                json.dumps(seed_data, indent=2) + "\n",
            )
            self.log(
                " Generated Antigravity seed "
                "(.gemini/antigravity/antigravity-instructions.md, antigravity.seed.json)"
            )
            return True
        except Exception as e:
            logger.warning(f"   Failed to generate Antigravity seed: {e}")
            return False

    def generate_copilot_seed(self) -> bool:
        """Generate GitHub Copilot bootstrap instructions."""
        try:
            copilot_dir = self.output_base / ".github"
            copilot_dir.mkdir(parents=True, exist_ok=True)
            fp_header = "\n".join(
                build_fingerprint_header(
                    self.spec_fingerprint, self.mandate_ids, self.generated_at
                )
            )
            content = build_copilot_instructions(fp_header)
            _write_root_seed_file(copilot_dir / "copilot-instructions.md", content)
            self.log(
                " Generated GitHub Copilot instructions (.github/copilot-instructions.md)"
            )
            return True
        except Exception as e:
            logger.warning(f"   Failed to generate Copilot instructions: {e}")
            return False

    def generate_claude_seed(self) -> bool:
        """Generate CLAUDE.md pointer with governance metadata."""
        try:
            skill_file = self.output_base / "CLAUDE.md"
            claude_dir = self.output_base / ".claude"
            hook_file = claude_dir / "providence-bootstrap.sh"
            settings_file = claude_dir / "settings.json"
            fp_header = "\n".join(
                build_fingerprint_header(
                    self.spec_fingerprint, self.mandate_ids, self.generated_at
                )
            )
            content = build_claude_md(fp_header)
            _write_root_seed_file(skill_file, content)
            claude_dir.mkdir(parents=True, exist_ok=True)
            write_text_utf8(hook_file, CLAUDE_BOOTSTRAP_SCRIPT)
            hook_file.chmod(0o755)
            write_text_utf8(settings_file, CLAUDE_SETTINGS)
            self.log(" Generated CLAUDE.md pointer and Claude bootstrap hook")
            return True
        except Exception as e:
            logger.warning(f"   Failed to generate CLAUDE.md: {e}")
            return False

    def generate_codex_seed(self) -> bool:
        """Generate Codex governance bootstrap seed."""
        try:
            codex_dir = self.output_base / ".codex"
            codex_dir.mkdir(parents=True, exist_ok=True)
            seed_data = {
                "auto_activate": True,
                "agent": "codex",
                "description": "Codex governance bootstrap  routes command aliases through .codex/commands.md",
                "load_compiled_from": RUNTIME_DIRNAME,
                "commands_ref": ".codex/commands.md",
                "governance_fingerprint": self.spec_fingerprint,
                "mandates_count": len(self.mandate_ids),
                "auto_load": True,
                "triggers": ["on_project_load", "on_editor_focus"],
                "required_context": [
                    f"{RUNTIME_DIRNAME}/metadata.json",
                    ".codex/commands.md",
                ],
                "on_load": "prepare_ide_context",
                "generated_at": self.generated_at,
            }
            write_text_utf8(
                self.seedlings_dir / "codex.seed.json",
                json.dumps(seed_data, indent=2) + "\n",
            )
            self.log(" Generated Codex seed (.providence/seedlings/codex.seed.json)")
            return True
        except Exception as e:
            logger.warning(f"   Failed to generate Codex seed: {e}")
            return False
