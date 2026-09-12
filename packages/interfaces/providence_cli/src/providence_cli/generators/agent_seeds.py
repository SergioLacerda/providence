"""Generate AI agent seed configurations.

Public API  all implementations live in private submodules:
- _shared.py          Fingerprint utils + _render_instruction_document
- _seeds.py           Standalone agent seed orchestrator (.providence-centric guidance)
- _seeds_platforms.py    Per-platform agent seed renderers
- _instruction_files.py  IDE-specific instruction files (.github/, .claude/, etc.)
- _prompt_commands.py    CLI prompt/command files (CLAUDE.md, .github/prompts/, etc.)
"""

from ._instruction_files import (
    generate_agent_instruction_files,
    generate_copilot_instructions,
)
from ._prompt_commands import generate_agent_prompt_commands
from ._seeds import generate_agent_seeds
from ._seeds_platforms import (
    _generate_antigravity_seed,
    _generate_claude_seed,
    _generate_copilot_seed,
    _generate_cursor_seed,
    _generate_gemini_seed,
    _generate_generic_seed,
)
from ._shared import _fingerprint_prefix, _render_instruction_document

__all__ = [
    "generate_agent_seeds",
    "generate_agent_instruction_files",
    "generate_copilot_instructions",
    "generate_agent_prompt_commands",
    # Seed generators (accessed by tests)
    "_generate_cursor_seed",
    "_generate_copilot_seed",
    "_generate_generic_seed",
    "_generate_claude_seed",
    "_generate_gemini_seed",
    "_generate_antigravity_seed",
    # Internal helpers
    "_fingerprint_prefix",
    "_render_instruction_document",
]
