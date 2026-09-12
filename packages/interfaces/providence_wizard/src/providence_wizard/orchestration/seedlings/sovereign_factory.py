"""Sovereign Factory."""

import importlib.resources
import logging
import shutil
from pathlib import Path

from .base_generator import BaseSeedlingGenerator

logger = logging.getLogger(__name__)


def _resolve_template_src() -> Path:
    """Resolve the sovereign-factory template directory.

    Tries ``importlib.resources`` first (works correctly in installed packages
    and editable installs alike). Falls back to a ``__file__``-relative path
    for development environments where the package is not formally installed.
    """
    try:
        # importlib.resources.files() is available on Python 3.9+
        pkg_root = importlib.resources.files("providence_wizard")
        candidate = (
            Path(str(pkg_root)) / "templates" / "governance" / "sovereign-factory"
        )
        if candidate.exists():
            return candidate
    except (TypeError, AttributeError, ModuleNotFoundError):
        pass  # fall through to __file__-relative fallback below
    # Fallback: path relative to this source file
    return (
        Path(__file__).parent.parent.parent
        / "templates"
        / "governance"
        / "sovereign-factory"
    )


class SovereignFactoryGenerator(BaseSeedlingGenerator):
    """
    Generator for the Sovereign Factory seedling.

    This seedling provides:
    - Mission Triggers (Slash Commands)
    - Prompt Templates (.prompt.md)
    - Antigravity Skill integration
    """

    def generate_sovereign_factory_seed(self) -> bool:
        """
        Plant the Sovereign Factory seeds into the new project.
        """
        try:
            # 1. Resolve template source path using importlib.resources with fallback
            template_src = _resolve_template_src()

            if not template_src.exists():
                logger.warning(
                    f"   Sovereign Factory template not found at {template_src}"
                )
                return False

            # 2. Plant Prompt Templates
            prompts_dest = self.output_base / ".github" / "prompts"
            prompts_dest.mkdir(parents=True, exist_ok=True)

            src_prompts = template_src / "prompts"
            if src_prompts.exists():
                for prompt_file in src_prompts.glob("*.prompt.md"):
                    shutil.copy2(prompt_file, prompts_dest / prompt_file.name)
                self.log(
                    f" Planted {len(list(src_prompts.glob('*.prompt.md')))} mission prompts in .github/prompts/"
                )

            # 3. Plant Antigravity Skills (e.g. providence SKILL.md for Gemini CLI)
            src_antigravity = template_src / "antigravity"
            if src_antigravity.exists():
                antigravity_dest = self.output_base / ".gemini" / "antigravity"
                antigravity_dest.mkdir(parents=True, exist_ok=True)
                for item in src_antigravity.rglob("*"):
                    if item.is_file():
                        rel = item.relative_to(src_antigravity)
                        dest_file = antigravity_dest / rel
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_file)
                skill_count = sum(1 for _ in src_antigravity.rglob("*.md"))
                self.log(
                    f" Planted antigravity skills in .gemini/antigravity/ ({skill_count} files)"
                )

            return True
        except Exception as e:
            logger.error(f"   Failed to generate Sovereign Factory seed: {e}")
            return False
