"""Per-platform agent seed generators  Gemini, Antigravity."""

from typing import Any

from ._shared import _fingerprint_prefix, _format_rules


def _generate_gemini_seed(
    config: dict[str, Any],
    mandatory_rules: list[dict[str, Any]],
    customizable_items: list[dict[str, Any]],
) -> str:
    """Generate Gemini-specific agent seed."""
    client_fp = _fingerprint_prefix(config, "client_fingerprint")
    return f"""# Gemini Governance Context

## Workspace Snapshot
- **Client Fingerprint**: {client_fp}
- **Managed Items**: {len(config.get("items", []))}
- **Customizable Items**: {len(customizable_items)}

## Immutable Rules

{_format_rules(mandatory_rules)}

## Working Protocol
1. Confirm active governance items before code suggestions
2. Preserve architectural decisions and mandatory rules
3. Query compiled artifacts: `providence ask --full "<question>"`
4. Validate with `providence governance validate` before completion
"""


def _generate_antigravity_seed(
    config: dict[str, Any],
    mandatory_rules: list[dict[str, Any]],
    customizable_items: list[dict[str, Any]],
) -> str:
    """Generate Antigravity-specific agent seed."""
    core_fp = _fingerprint_prefix(config, "core_fingerprint")
    client_fp = _fingerprint_prefix(config, "client_fingerprint")
    return f"""# Antigravity Governance Context

## Governance Envelope
- **Core Fingerprint**: {core_fp}
- **Client Fingerprint**: {client_fp}
- **Managed Items**: {len(config.get("items", []))}
- **Customizable Items**: {len(customizable_items)}

## Mandatory Rules

{_format_rules(mandatory_rules)}

## Enforcement Notes
1. Treat governance mandates as non-negotiable
2. Use compiled artifacts as source of truth: `.providence/compiled/`
3. Query context: `providence ask --full "<question>"`
4. Run `providence governance validate` and `providence runtime status` before handoff
"""
