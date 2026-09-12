"""Governance redirector and instruction-document renderers for AI agent bootstrap files."""

from __future__ import annotations

from typing import Any

from providence_cli.generators._shared_helpers import (
    _collect_instruction_sections,
    _fingerprint_prefix,
    _item_description,
    _item_name,
)
from providence_cli.generators._shared_renderers import (
    _render_claude_bootstrap_sections,
)


def render_agent_redirector(
    tool_name: str,  # noqa: ARG001
    header_lines: list[str],
    fingerprint: str,
    mandate_ids: list[str],
) -> str:
    """Render a lightweight governance redirector for an AI agent instruction file.

    Mirror of providence_wizard._renderer.render_agent_redirector  keep output format in sync.
    Used by generate_agent_instruction_files() for all agents except Copilot.
    """
    ids_preview = ", ".join(mandate_ids[:5])
    if len(mandate_ids) > 5:
        ids_preview += ", ..."

    fp_lines = [
        f"# Governance fingerprint: {fingerprint[:16]}",
        f"# Active mandates: {len(mandate_ids)}"
        + (f" ({ids_preview})" if ids_preview else ""),
        "# Drift check: fingerprint must match .providence/metadata.json  fingerprints.combined",
    ]

    lines: list[str] = list(header_lines) + fp_lines
    lines += [
        "",
        "## Agent Entrypoint",
        "",
        "Bootstrap sequence for this agent starts with `.providence/agent-instructions.md`.",
        "",
        "## Entrypoint Contract",
        "",
        "1. You are under governance. Always resolve instructions from `.providence`.",
        "   Initial reference: `.providence/agent-instructions.md`",
        "",
        "## Commands And Skills (Source Of Truth)",
        "",
        "1. Commands source of truth: `.providence/commands`.",
        "2. Skills source of truth: `.providence/skills`.",
        "3. On startup, load:",
        "   - `.providence/commands/registry.json`",
        "   - `.providence/skills/registry.json`",
        "4. For each active command/skill in registries, read canonical files:",
        "   - Commands: `.providence/commands/<command-id>/command.yaml`",
        "   - Skills: `.providence/skills/<skill-name>/skill.yaml`",
        "5. Precedence rule:",
        "   - Local path is for context and ergonomics.",
        "   - `.providence` is authoritative for routing/policy and wins conflicts.",
        "",
        "## One Rule",
        "",
        "**Before planning, coding, or deciding:** read `.providence/agent-instructions.md`.",
        "",
        "## Quick Reference",
        "",
        "| File | Purpose |",
        "|------|---------|",
        "| `.providence/agent-instructions.md` | **START HERE**  Complete agent bootstrap |",
        "| `.providence/metadata.json` | Workspace version, fingerprints, item counts |",
        "| `.providence/source/governance-core.json` | Human-readable mandates snapshot |",
        "| `.providence/source/mandates/mandates.md` | Full mandate descriptions |",
        "",
        "## Validation",
        "",
        "Before finalizing changes, run:",
        "",
        "```bash",
        "providence governance validate",
        "providence runtime status",
        "```",
        "",
        "If `providence` is not found on your shell `PATH`, run it via `uv run",
        "providence <command>` instead  see `docs/guides/ONBOARDING.md` for why.",
        "",
        "## Safe Fallback",
        "",
        "If registries or canonical files are missing/inconsistent, register bootstrap drift",
        "and continue in safe fallback mode without inventing missing rules.",
        "",
    ]
    return "\n".join(lines)


def _render_instruction_document(
    tool_name: str, header_lines: list[str], config: dict[str, Any]
) -> str:
    """Render a governance instruction document from compiled items.

    For Claude, adds bootstrap sequence, two-question quiz, context navigation,
    and git protocol sections derived from compiled governance artifacts.
    """
    sections = _collect_instruction_sections(config)
    mandates = sections["mandates"]
    guidelines = sections["guidelines"]
    decisions = sections["decisions"]

    lines: list[str] = list(header_lines)
    lines += [
        "",
        "## Workspace Governance",
        "",
        f"This {tool_name} workspace is governed by SDD compiled artifacts.",
        f"Core fingerprint: {_fingerprint_prefix(config, 'core_fingerprint', 16)}",
        f"Client fingerprint: {_fingerprint_prefix(config, 'client_fingerprint', 16)}",
        f"Items loaded: {len(sections['items'])}",
        "",
    ]

    if mandates:
        lines += [
            "## Mandatory Rules (MANDATES)",
            "",
            "These rules are immutable and must be enforced in every implementation:",
            "",
        ]
        for mandate in mandates:
            mid = mandate.get("id", "")
            name = _item_name(mandate) or mid
            desc = _item_description(mandate)
            lines.append(f"- **[{mid}] {name}**: {desc}")
        lines.append("")

    if guidelines:
        lines += ["## Guidelines (SOFT)", ""]
        for guideline in guidelines:
            gid = guideline.get("id", "")
            name = _item_name(guideline) or gid
            desc = _item_description(guideline)
            lines.append(f"- **[{gid}] {name}**: {desc}")
        lines.append("")

    if decisions:
        lines += ["## Architectural Decisions", ""]
        for decision in decisions:
            did = decision.get("id", "")
            name = _item_name(decision) or did
            status = decision.get("status", "")
            desc = _item_description(decision)
            status_tag = f" `{status}`" if status else ""
            lines.append(f"- **[{did}]{status_tag} {name}**: {desc}")
        lines.append("")

    if not (mandates or guidelines or decisions):
        lines += [
            "## Governance Context",
            "",
            "This workspace is governed by SDD (Spec Driven Development).",
            "Run `providence governance compile` to build governance artifacts.",
            "",
        ]

    if tool_name == "Claude":
        lines += _render_claude_bootstrap_sections()

    lines += [
        "## Validation",
        "",
        "Run `providence governance validate` before commits.",
        "Run `providence runtime status` to check workspace health.",
        "",
    ]
    return "\n".join(lines)
