"""Seedling output templates: ACTIVATION_GUIDE.md, verify.py, agent-instructions.md, AGENTS.md."""

from __future__ import annotations

from providence_wizard.templates._activation_guide_template import (
    build_activation_guide,
)
from providence_wizard.templates._agent_instructions_template import (
    build_agent_instructions,
)
from providence_wizard.templates._agents_md_template import build_agents_md
from providence_wizard.templates._verification_script_template import (
    build_verification_script,
)

__all__ = [
    "build_activation_guide",
    "build_agent_instructions",
    "build_agents_md",
    "build_verification_script",
]
