"""Constants and pure string builders for prompt command generation."""

from __future__ import annotations

from typing import Any

_COMMANDS_TABLE = (
    "| Task | Command |\n"
    "|------|---------|\n"
    "| Run tests | `providence test run` |\n"
    "| Lint | `providence lint run` |\n"
    "| Validate governance | `providence governance validate` |\n"
    "| Compile governance | `providence governance compile` |\n"
    "| Runtime status | `providence runtime status` |\n"
    '| Query context | `providence ask --full "<question>"` |\n'
    '| Organize large context | `providence organize "<context>"` |\n'
    "| Diagnostics | `providence doctor run --mode real` |\n"
    "| Generate agent seeds | `providence governance generate` |\n"
)

_RUNTIME_STATUS_NOTE = (
    "Exit codes for `providence runtime status`: "
    "0=HEALTHY, 1=NOT_INITIALIZED, 2=MISCONFIGURED, 3=NOT_CONNECTED.\n"
)

_SOFT_GOVERNANCE_CHECK = (
    "\nPROVIDENCE GOVERNANCE CHECK\n"
    "- Always end responses with this compact footer:\n"
    "  `PROVIDENCE GOVERNANCE: drift=${status} | governance=${status} | profile=${profile}`\n"
)

_HARD_MODE_FIELD_CONTRACT = (
    "\nHard-mode governance fields:\n"
    "- Preserve and report `execution_gate`, `gate_reason`, `intake_index_mode`,\n"
    "  `intake_chunks`, and `governance_mode` when command output includes them.\n"
    "- Preserve delegation/provider-binding signals such as `delegation_status`,\n"
    "  `delegation_executed`, and `provider_bound` when present.\n"
    "- If `execution_gate: blocked`, stop and report `gate_reason`.\n"
    "- If `execution_gate: allowed`, continue only within the command or skill contract.\n"
    "- `intake_index_mode: none` is independent from `execution_gate`; surface it\n"
    "  by name and value, and do not describe it as a blocked gate unless\n"
    "  `execution_gate: blocked` is also present.\n"
)

_AUDIT_JSON_NOTE = (
    "\nAudit JSON policy:\n"
    "- `.providence/compiled/audit/*.json` is human/audit oriented.\n"
    "- Agents should prefer `.providence/source/*` for human-readable governance context and\n"
    "  runtime checks (`providence runtime status`, `providence ask --full`) for operational state.\n"
)

__all__ = [
    "_AUDIT_JSON_NOTE",
    "_COMMANDS_TABLE",
    "_HARD_MODE_FIELD_CONTRACT",
    "_RUNTIME_STATUS_NOTE",
    "_SOFT_GOVERNANCE_CHECK",
]

_ASK_500_FALLBACK_NOTE = (
    "\nOperational fallback (IDE/API failures):\n"
    "- If the IDE/provider returns `API Error: 5xx`, stop IDE retry loops for this turn.\n"
    "- Run local fallback immediately in terminal:\n"
    '  `providence ask --full "$QUERY"`\n'
    "- Capture and report the provider `request_id` for incident triage.\n"
)


def _slash_aliases_markdown(aliases: list[tuple[str, str]]) -> str:
    """Return markdown table of slash aliases."""
    lines = [
        "## Slash aliases (`/sdd-*`)",
        "",
        "| Alias | Adapter target |",
        "|------|----------------|",
    ]
    for slash, cmd_id in aliases:
        lines.append(f"| `{slash}` | `.codex/skills/{cmd_id}.prompt.md` |")
    lines.append("")
    return "\n".join(lines)


def _prompt_spec_for_command(command: dict[str, Any]) -> tuple[str, str, str, str]:
    """Build prompt metadata/body from a canonical command entry."""
    slug = str(command.get("id", "")).strip()
    route = command.get("routes_to", {})
    route_type = str(route.get("type", "")).strip() if isinstance(route, dict) else ""

    if slug == "sdd-ask":
        return (
            slug,
            "Query Providence governance context",
            "agent",
            "Query the SDD governance context with the user's question.\n\n"
            'Execute in the terminal:\n```bash\nprovidence runtime status\nprovidence governance validate\nprovidence ask --full "$QUERY"\n```\n\n'
            "Replace `$QUERY` with the user's question.\n\n"
            "HARD contract for this command:\n"
            "- Run preflight in order (`providence runtime status` then `providence governance validate`).\n"
            "- If preflight fails, do not continue; return governance-blocked status.\n"
            "- Only continue to `providence ask --full` when preflight is healthy.\n"
            '- For large/noisy input, run `providence organize "$QUERY"` first and consume indexed chunks only.\n\n'
            + _HARD_MODE_FIELD_CONTRACT
            + "\n\n"
            "Response contract:\n"
            "- Show `fingerprint`, `context_source`, and `mandates_loaded` from runtime output.\n"
            "- Treat `.providence` runtime artifacts as source of truth for these fields.\n"
            + _ASK_500_FALLBACK_NOTE,
        )

    if slug == "sdd-organize":
        return (
            slug,
            "Prepare indexed context for large inputs",
            "agent",
            "Prepare large/noisy input before diagnosis or ask.\n\n"
            'Execute in the terminal:\n```bash\nprovidence organize "$QUERY"\n```\n\n'
            "Use `.providence/runtime/ask-intake/` artifacts for selective retrieval.\n"
            + _HARD_MODE_FIELD_CONTRACT,
        )

    if route_type == "cli" and isinstance(route, dict):
        cli_command = str(route.get("command", "")).strip()
        return (
            slug,
            f"Run {cli_command}",
            "agent",
            "Run the mapped SDD CLI command.\n\n"
            f"Execute in the terminal:\n```bash\n{cli_command}\n```\n"
            + _HARD_MODE_FIELD_CONTRACT,
        )

    if route_type == "skill" and isinstance(route, dict):
        skill_id = str(route.get("id", "")).strip()
        return (
            slug,
            f"Run governed skill {skill_id}",
            "agent",
            "Run the mapped governed skill through the runtime engine.\n\n"
            f"Execute in the terminal:\n```bash\nprovidence skills run {skill_id}\n```\n"
            + _HARD_MODE_FIELD_CONTRACT,
        )

    return (
        slug,
        f"Run {slug}",
        "agent",
        "Run the mapped governed operation for this command as defined in "
        "`.providence/commands/registry.json`." + _HARD_MODE_FIELD_CONTRACT,
    )
