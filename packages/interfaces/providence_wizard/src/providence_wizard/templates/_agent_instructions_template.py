"""Thin wrapper over the canonical .providence/agent-instructions.md template.

Kept for the initial wizard seedling path's existing call signature; the
actual content lives in `orchestration.seedlings._agent_instructions_content`
(see SQ-004 consolidation  the two templates previously drifted independently).
"""

from __future__ import annotations

from providence_wizard.orchestration.seedlings._agent_instructions_content import (
    build_agent_instructions_content,
)


def build_agent_instructions(
    spec_fingerprint: str,
    generated_at: str,
    mandates_list: str,
    mandate_count: int = 0,
    ids_preview: str = "",
) -> str:
    """Render .providence/agent-instructions.md content for the initial seedling path."""
    return build_agent_instructions_content(
        fingerprint=spec_fingerprint,
        generated_at=generated_at,
        mandate_count=mandate_count,
        ids_preview=ids_preview,
        mandates_list=mandates_list,
        initial_seedling=True,
    )
