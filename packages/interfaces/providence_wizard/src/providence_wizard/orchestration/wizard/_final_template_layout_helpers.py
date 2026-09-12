"""Context-cache scaffolding shared by final-template consolidation and layout."""

from __future__ import annotations

from pathlib import Path

CONTEXT_CACHE_TEMPLATE = """# SDD Context Cache (M003)

## Current Objective
- [ ] Define objective

## Active Sub-task
- [ ] Define active sub-task

## Completed Milestones
- None yet

## Shared Variables/States
- Profile: unknown
- Governance fingerprint: unknown

## Pending Risks
- None

## Validation Quiz
- Pending
"""


def ensure_context_cache(target_dir: Path, cache_relative_path: str) -> None:
    """Ensure the context cache file exists (M003 requirement)."""
    cache_file = target_dir / cache_relative_path
    if cache_file.exists():
        return
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(CONTEXT_CACHE_TEMPLATE, encoding="utf-8")
