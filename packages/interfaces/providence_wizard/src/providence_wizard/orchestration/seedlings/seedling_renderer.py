"""SeedlingRenderer  markdown and script artifact generation for seedlings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from providence_core.utils.managed_block import merge_managed_block
from providence_core.utils.text_io import read_text_utf8
from providence_wizard.constants import RUNTIME_DIRNAME
from providence_wizard.templates.seedling_templates import (
    build_activation_guide,
    build_agent_instructions,
    build_agents_md,
    build_verification_script,
)

if TYPE_CHECKING:
    from .base_generator import BaseSeedlingGenerator


class SeedlingRenderer:
    """Render ACTIVATION_GUIDE.md, verify.py, agent-instructions.md, AGENTS.md."""

    def __init__(self, ctx: BaseSeedlingGenerator) -> None:
        self._ctx = ctx

    def generate_activation_guide(self) -> bool:
        """Generate ACTIVATION_GUIDE.md."""
        try:
            ctx = self._ctx
            guide_file = ctx.seedlings_dir / "ACTIVATION_GUIDE.md"
            enforcement_mode = ctx.config.get("enforcement_mode", "warn_mode")
            enforcement_labels = {
                "silent_mode": "Sem Alertas (Silent)",
                "warn_mode": "Alertas (Warnings only)",
                "strict_mode": "Bloquear (Strict enforcement)",
            }
            enforcement_label = enforcement_labels.get(
                enforcement_mode, "Alertas (Warnings)"
            )
            enforcement_explanations = {
                "silent_mode": "No warnings when violations detected - suitable for learning and experiments",
                "warn_mode": "Show warnings but allow violations to continue - flexible during development",
                "strict_mode": "Block violations in CI pipeline - strict enforcement for production",
            }
            enforcement_explanation = enforcement_explanations.get(
                enforcement_mode, "Show warnings only"
            )
            enforcement_behavior = (
                "- **Violations are SILENT**: No warnings or errors, just logging"
                if enforcement_mode == "silent_mode"
                else (
                    "- **Violations show WARNINGS**: Notifications in IDE/logs but no blocking"
                    if enforcement_mode == "warn_mode"
                    else "- **Violations are BLOCKED**: CI pipeline blocks merge/release with violations"
                )
            )
            content = build_activation_guide(
                fingerprint=ctx.spec_fingerprint,
                generated_at=ctx.generated_at,
                enforcement_label=enforcement_label,
                enforcement_explanation=enforcement_explanation,
                enforcement_behavior=enforcement_behavior,
                language=ctx.config.get("language", "python").upper(),
                mandates_list="\n".join(
                    f" {m['id']}: {m.get('title', 'Unknown')}" for m in ctx.mandates
                ),
                guidelines_list=(
                    "\n".join(f" {cat.upper()}" for cat in ctx.active_categories)
                    if ctx.active_categories
                    else "(None configured)"
                ),
                mandate_ids_joined=", ".join(ctx.mandate_ids),
            )
            with open(guide_file, "w", encoding="utf-8") as f:
                f.write(content)
            ctx.log(" Generated ACTIVATION_GUIDE.md")
            return True
        except Exception as e:
            self._ctx._emit(f"   Failed to generate activation guide: {e}")
            return False

    def generate_verification_script(self) -> bool:
        """Generate verify.py."""
        try:
            ctx = self._ctx
            script_file = ctx.seedlings_dir / "verify.py"
            content = build_verification_script(
                mandate_ids_str="', '".join(ctx.mandate_ids)
            )
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(content)
            script_file.chmod(0o755)
            ctx.log(" Generated verify.py")
            return True
        except Exception as e:
            self._ctx._emit(f"   Failed to generate verification script: {e}")
            return False

    def generate_agnostic_agent_instructions(self) -> bool:
        """Generate .providence/agent-instructions.md."""
        try:
            ctx = self._ctx
            instructions_dir = ctx.output_base / RUNTIME_DIRNAME
            instructions_dir.mkdir(parents=True, exist_ok=True)
            mandates_lines = []
            for m in ctx.mandates:
                title = m.get("title", "Unknown")
                desc = m.get("description", m.get("summary", ""))
                if desc:
                    mandates_lines.append(f"- **{m['id']}**: {title} ({desc})")
                else:
                    mandates_lines.append(f"- **{m['id']}**: {title}")
            ids_preview = ", ".join(ctx.mandate_ids[:5])
            if len(ctx.mandate_ids) > 5:
                ids_preview += ", ..."
            content = build_agent_instructions(
                spec_fingerprint=ctx.spec_fingerprint,
                generated_at=ctx.generated_at,
                mandates_list="\n".join(mandates_lines),
                mandate_count=len(ctx.mandate_ids),
                ids_preview=ids_preview,
            )
            instructions_file = instructions_dir / "agent-instructions.md"
            with open(instructions_file, "w", encoding="utf-8") as f:
                f.write(content)
            ctx.log(" Generated agnostic .providence/agent-instructions.md")
            return True
        except Exception as e:
            self._ctx._emit(f"   Failed to generate agnostic agent instructions: {e}")
            return False

    def generate_agents_md(self) -> bool:
        """Generate root AGENTS.md."""
        try:
            ctx = self._ctx
            agents_file = ctx.output_base / "AGENTS.md"
            ids_preview = ", ".join(ctx.mandate_ids[:5])
            if len(ctx.mandate_ids) > 5:
                ids_preview += ", ..."
            content = build_agents_md(
                spec_fingerprint=ctx.spec_fingerprint,
                generated_at=ctx.generated_at,
                mandate_count=len(ctx.mandate_ids),
                ids_preview=ids_preview,
            )
            existing = read_text_utf8(agents_file) if agents_file.exists() else None
            merged = merge_managed_block(existing, content)
            agents_file.write_text(merged, encoding="utf-8")
            ctx.log(" Generated AGENTS.md bootstrap contract")
            return True
        except Exception as e:
            self._ctx._emit(f"   Failed to generate AGENTS.md: {e}")
            return False
