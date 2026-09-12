"""Governance Seeds."""

import logging
from pathlib import Path
from typing import Any

from providence_wizard.constants import RUNTIME_DIRNAME

from ._agent_instructions_content import build_agent_instructions_content
from .base_generator import BaseSeedlingGenerator
from .guideline_seeds import GuidelineSeeds
from .mandate_seeds import MandateSeeds
from .seedling_renderer import SeedlingRenderer

logger = logging.getLogger(__name__)


class GovernanceSeedsGenerator(BaseSeedlingGenerator):
    """GovernanceSeedsGenerator."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._mandate_seeds = MandateSeeds(self)
        self._renderer = SeedlingRenderer(self)
        self._cmd_seeds = GuidelineSeeds(self)

    @property
    def prompt_commands_mode(self) -> str:
        """Current prompt-commands generation mode."""
        return self._cmd_seeds.prompt_commands_mode

    # --- backwards-compat proxies for tests and callers that access private helpers ---

    def _should_auto_activate(self) -> bool:
        return self._mandate_seeds._should_auto_activate()

    def _resolve_skill_set(self) -> list[str]:
        return self._mandate_seeds._resolve_skill_set()

    def _resolve_activation_profile(self) -> str:
        return self._mandate_seeds._resolve_activation_profile()

    def _resolve_escalation_mode(self) -> str:
        return self._mandate_seeds._resolve_escalation_mode()

    def _generate_minimal_prompt_commands(self) -> bool:
        return self._cmd_seeds._generate_minimal_prompt_commands()

    def _normalize_prompt_command_outputs(self, results: Any) -> list[Any]:
        return self._cmd_seeds._normalize_prompt_command_outputs(results)

    @property
    def _prompt_commands_mode(self) -> str:
        return self._cmd_seeds.prompt_commands_mode

    @_prompt_commands_mode.setter
    def _prompt_commands_mode(self, value: str) -> None:
        self._cmd_seeds.prompt_commands_mode = value

    @property
    def _prompt_commands_outputs(self) -> list[str]:
        return self._cmd_seeds.prompt_commands_outputs

    @_prompt_commands_outputs.setter
    def _prompt_commands_outputs(self, value: list[str]) -> None:
        self._cmd_seeds.prompt_commands_outputs = value

    # --- end backwards-compat proxies ---

    def generate_governance_seed(self) -> bool:
        """Generate governance.seed.json activation artifact."""
        return self._mandate_seeds.generate_governance_seed()

    def generate_compliance_seed(self) -> bool:
        """Generate compliance.seed.json CI/CD artifact."""
        return self._mandate_seeds.generate_compliance_seed()

    def generate_activation_guide(self) -> bool:
        """Generate ACTIVATION_GUIDE.md for manual agent onboarding."""
        return self._renderer.generate_activation_guide()

    def generate_verification_script(self) -> bool:
        """Generate verify.py governance health-check script."""
        return self._renderer.generate_verification_script()

    def generate_agnostic_agent_instructions(self) -> bool:
        """Generate agent-agnostic .providence/agent-instructions.md."""
        return self._renderer.generate_agnostic_agent_instructions()

    def generate_prompt_commands(self) -> bool:
        """Generate IDE prompt-command files for all configured agents."""
        return self._cmd_seeds.generate_prompt_commands()

    def generate_ai_instructions(self) -> bool:
        """No-op placeholder  AI instructions are agent-specific."""
        return self._cmd_seeds.generate_ai_instructions()

    def generate_openai_instructions(self) -> bool:
        """No-op placeholder  OpenAI instructions are agent-specific."""
        return self._cmd_seeds.generate_openai_instructions()

    def generate_agents_md(self) -> bool:
        """Generate AGENTS.md bootstrap contract for agent discovery."""
        return self._renderer.generate_agents_md()

    def get_summary(self) -> dict[str, Any]:
        """Return a dict describing all generated seedling artifacts."""
        seedling_files = [
            ("governance.seed.json", "GAP v1.0"),
            ("agent-prep.seed.json", "IDE hooks  all agents"),
            ("compliance.seed.json", "CI/CD"),
            ("copilot.seed.json", "GitHub Copilot redirector"),
            ("gemini.seed.json", "Gemini redirector"),
            ("vscode.seed.json", "VS Code redirector"),
            ("cursor.seed.json", "Cursor IDE redirector"),
            ("claude.seed.json", "Claude Code redirector"),
            ("codex.seed.json", "Codex redirector"),
            ("ACTIVATION_GUIDE.md", "Instructions"),
            ("verify.py", "Verification script"),
        ]
        files = [
            f"{name} ({description})"
            for name, description in seedling_files
            if (self.seedlings_dir / name).exists()
        ]
        if (self.output_base / "AGENTS.md").exists():
            files.append("AGENTS.md (Agent bootstrap contract)")
        outputs = self._cmd_seeds.prompt_commands_outputs
        if outputs:
            files.append("prompt commands: " + ", ".join(outputs))
        return {
            "seedlings_dir": str(self.seedlings_dir),
            "count": len(files),
            "files": files,
            "fingerprint": self.spec_fingerprint,
            "mandates": self.mandate_ids,
            "guidelines": self.active_categories,
            "adoption_level": self.config.get("adoption_level", "standard"),
            "language": self.config.get("language", "python"),
            "generated_at": self.generated_at,
            "awareness_pack": {
                "prompt_commands_mode": self._cmd_seeds.prompt_commands_mode,
                "prompt_commands_outputs": self._cmd_seeds.prompt_commands_outputs,
            },
        }


def generate_agent_instructions_from_config(
    output_base: "Path",
    config: "dict[str, Any]",
) -> bool:
    """Regenerate .providence/agent-instructions.md from a governance config dict."""
    from datetime import datetime, timezone
    from pathlib import Path

    try:
        items = config.get("items", [])
        mandates = [i for i in items if str(i.get("type", "")).upper() == "MANDATE"]
        fingerprint = str(
            config.get("core_fingerprint") or config.get("fingerprint") or "unknown"
        )[:16]
        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        mandate_ids = [m.get("id", "") for m in mandates if m.get("id")]
        mandates_lines = []
        for m in mandates:
            title = m.get("title", m.get("name", "Unknown"))
            desc = m.get("description", m.get("summary", ""))
            if desc:
                mandates_lines.append(f"- **{m.get('id', '?')}**: {title} ({desc})")
            else:
                mandates_lines.append(f"- **{m.get('id', '?')}**: {title}")
        mandates_list = (
            "\n".join(mandates_lines)
            if mandates_lines
            else "(none  run providence governance compile)"
        )
        ids_preview = ", ".join(mandate_ids[:5])
        if len(mandate_ids) > 5:
            ids_preview += ", ..."
        instructions_dir = Path(output_base) / RUNTIME_DIRNAME
        instructions_dir.mkdir(parents=True, exist_ok=True)
        instructions_file = instructions_dir / "agent-instructions.md"
        content = build_agent_instructions_content(
            fingerprint=fingerprint,
            generated_at=generated_at,
            mandate_count=len(mandate_ids),
            ids_preview=ids_preview,
            mandates_list=mandates_list,
        )
        with open(instructions_file, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        logging.getLogger(__name__).warning(
            f"Failed to regenerate agent-instructions.md: {e}"
        )
        return False


def generate_root_bootstrap_from_config(
    output_base: "Path",
    config: "dict[str, Any]",
) -> bool:
    """Regenerate root bootstrap files from a compiled governance config dict."""
    from datetime import datetime, timezone
    from pathlib import Path

    from providence_core.utils.text_io import write_text_utf8
    from providence_wizard.templates.seedling_templates import build_agents_md

    from ._ai_seed_templates import build_claude_md
    from ._renderer import build_fingerprint_header, render_agent_redirector

    try:
        items = config.get("items", [])
        mandates = [i for i in items if str(i.get("type", "")).upper() == "MANDATE"]
        fingerprint = str(
            config.get("core_fingerprint") or config.get("fingerprint") or "unknown"
        )[:16]
        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        mandate_ids = [str(m.get("id", "")) for m in mandates if m.get("id")]
        ids_preview = ", ".join(mandate_ids[:5])
        if len(mandate_ids) > 5:
            ids_preview += ", ..."

        output = Path(output_base)
        fp_header = "\n".join(
            build_fingerprint_header(fingerprint, mandate_ids, generated_at)
        )
        write_text_utf8(output / "CLAUDE.md", build_claude_md(fp_header))
        write_text_utf8(
            output / "GEMINI.md",
            render_agent_redirector(
                tool_name="Gemini",
                config_paths=[
                    ".gemini/commands.md",
                    ".gemini/antigravity/skills/",
                    "GEMINI.md",
                ],
                fingerprint=fingerprint,
                mandate_ids=mandate_ids,
                generated_at=generated_at,
            ),
        )
        write_text_utf8(
            output / "AGENTS.md",
            build_agents_md(
                spec_fingerprint=fingerprint,
                generated_at=generated_at,
                mandate_count=len(mandate_ids),
                ids_preview=ids_preview,
            ),
        )
        return True
    except Exception as e:
        logging.getLogger(__name__).warning(
            f"Failed to regenerate root bootstrap files: {e}"
        )
        return False
