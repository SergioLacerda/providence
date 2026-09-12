"""Template for the root AGENTS.md."""

from __future__ import annotations


def build_agents_md(
    spec_fingerprint: str,
    generated_at: str,
    mandate_count: int,
    ids_preview: str,
) -> str:
    """Render root AGENTS.md content."""
    preview_str = f" ({ids_preview})" if ids_preview else ""
    return f"""# Agent Bootstrap Paths
<!-- Governance fingerprint: {spec_fingerprint} -->
<!-- Active mandates: {mandate_count}{preview_str} -->
<!-- Generated: {generated_at} -->
<!-- Drift check: fingerprint must match .providence/metadata.json  fingerprints.combined -->

Objective: standardize where each agent must load local instructions, commands, and skills in this project.

## Mandatory Rules

1. Always prioritize local project files/folders before global sources.
2. On startup, each agent must read its dedicated path(s) listed below.
3. If `SKILL.md`, `*.md`, `commands/`, `prompts/`, or equivalent files exist, load them as operational context.
4. You are under governance: always resolve authoritative rules from `.providence`.
   Initial reference: `.providence/agent-instructions.md`.

## Governance Authority (`.providence`)

1. Governance is mandatory and authoritative from `.providence`.
2. Initial reference: `.providence/agent-instructions.md`.
3. If any local/global convenience file conflicts with `.providence`, follow `.providence`.

## Commands And Skills (Source Of Truth)

1. Commands source of truth: `.providence/commands`.
2. Skills source of truth: `.providence/skills`.
3. On startup, agents must load:
   - `.providence/commands/registry.json`
   - `.providence/skills/registry.json`
4. For each active command/skill in the registries, agents must read canonical files before use:
   - Commands: `.providence/commands/<command-id>/command.yaml`
   - Skills: `.providence/skills/<skill-name>/skill.yaml`
5. If registry or canonical file is missing/inconsistent, register bootstrap drift and continue in safe fallback mode without inventing missing rules.

## Agent-Specific Paths

- Codex: `./.codex/`
- Claude: `./CLAUDE.md`, `./.claude/commands/`
- Gemini: `./.gemini/`
- GitHub Copilot: `./.github/copilot-instructions.md`, `./.github/prompts/`
- Cursor: `./.cursor/rules/`
- VS Code Prompts: `./.github/prompts/`
## Minimal Fallback

If a dedicated path does not exist:

1. Register that local bootstrap is missing.
2. Continue with default agent behavior, without inventing local context.
"""
